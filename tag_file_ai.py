import base64
import json
import shutil
from datetime import datetime
from typing import Any, Union, Optional

import anchorpoint as ap
import apsync as aps
import os
import tempfile
import hashlib

import requests

from ai.api import init_anthropic_key, ANTHROPIC_API_URL, ANTHROPIC_API_VERSION, extract_json
from ai.response_schema import get_file_properties, get_file_schema_prompt
from ap_tools.dialogs import CreateTagFilesDialogData, create_tag_files_dialog
from common.logging import log, log_err
from image.resize import resize_image
from labels.attributes import ensure_attribute, replace_tag, check_or_update_attribute
from labels.extensions import extensions_without_preview, filter_ignored_extensions
from labels.variants import types_variants, genres_variants, objects_variants
from ai.constants import IMAGE_TOKENS_ESTIMATE, INPUT_TOKEN_PRICE, OUTPUT_TOKEN_PRICE, MAX_RETRIES, DEFAULT_MODEL
from ai.tokens import count_tokens
from common.settings import tagger_settings

prompt = (
    "You are a file tagging AI. When asked, write tags for each file in the order they were presented: "
)

if tagger_settings.file_label_ai_types:
    prompt += "content types (Texture, Sprite, Model, VFX, SFX, etc.) (min 1),"

if tagger_settings.file_label_ai_genres:
    prompt += "detailed genres (min 1),"

if tagger_settings.file_label_ai_objects:
    prompt += f"objects and other keywords in the image (min {tagger_settings.file_label_ai_objects_min}, max {tagger_settings.file_label_ai_objects_max}), "

prompt += "fill all tags for each image. Use Capitalized Words. IMPORTANT: Never repeat the same tag across different categories — each tag value must appear only once total."

naming_rules = tagger_settings.get_naming_rules()
if naming_rules:
    prompt += "\n\nCustom naming convention rules:\n" + naming_rules

output_token_count = 200

images_per_request = 10
proceed_dialog: ap.Dialog

all_variants = {
    "AI-Types": types_variants,
    "AI-Genres": genres_variants,
    "AI-Objects": objects_variants
}

items = get_file_properties()

schema_prompt = get_file_schema_prompt(items)


def calculate_file_hash(file_path, hash_algorithm="sha256", length: int = 8):
    hash_func = hashlib.new(hash_algorithm)

    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            hash_func.update(chunk)

    return hash_func.hexdigest()[:length]


def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def create_temp_directory():
    # Create a temporary directory
    temp_dir_root = os.path.join(tempfile.gettempdir(), "anchorpoint", "ai_tagger", "previews")
    if not os.path.exists(temp_dir_root):
        os.makedirs(temp_dir_root)

    return temp_dir_root


def get_preview_image(workspace_id, input_path, output_folder):
    file_hash = calculate_file_hash(input_path)

    # get the proper filename, rename it because the generated PNG file has a _pt appendix
    file_name = os.path.basename(input_path).split(".")[0]

    image_path = os.path.join(output_folder, f"{file_name}_{file_hash}_pt.png")

    existing_preview = aps.get_thumbnail(input_path, False)
    if existing_preview:
        # copy the existing preview to the output folder because we can not modify the existing preview
        if not os.path.exists(image_path):
            os.makedirs(output_folder, exist_ok=True)

        shutil.copy(existing_preview, image_path)

        log(f"Existing preview found: {existing_preview}\nCopying to {image_path}")
        return image_path

    log(f"Existing preview not found for {input_path}, generating new one")

    if not os.path.exists(image_path):
        aps.generate_thumbnails(
            [input_path],
            output_folder,
            with_detail=False,
            with_preview=True,
            workspace_id=workspace_id,
        )
        generated_path = os.path.join(output_folder, f"{file_name}_pt.png")
        if not os.path.exists(generated_path):
            # preview was not generated
            return ""
        log(f"Generated preview for {input_path}")

        os.rename(generated_path, image_path)
    else:
        log(f"Load cached preview for {input_path}")

    return image_path


ANTHROPIC_API_KEY = init_anthropic_key()


def get_claude_response_images(in_prompt, image_paths: list[str], model=DEFAULT_MODEL) -> list[Any]:
    if len(image_paths) == 0 or len(image_paths) > images_per_request:
        raise ValueError(f"The number of images should be between 1 and {images_per_request}")

    uploads = [(encode_image(image_path), "image/png" if image_path.lower().endswith(".png") else "image/jpeg") for image_path in image_paths]
    from common.filename import clean_character_filename
    # Send full original paths so the AI can use folder structure for tagging
    # Preprocess Ch_ filenames to strip animation states
    original_file_paths = [clean_character_filename(original_files.get(p, p)).replace("\\", "/") for p in image_paths]

    content = [{
        "type": "text",
        "text": "Please tag these images (use both the filename and folder path for context):\n" + "\n".join(original_file_paths)
    }]
    for data, media_type in uploads:
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": media_type,
                "data": data
            }
        })

    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": ANTHROPIC_API_VERSION,
        "Content-Type": "application/json"
    }

    payload = {
        "model": model,
        "max_tokens": 4096,
        "system": in_prompt + schema_prompt,
        "messages": [
            {"role": "user", "content": content}
        ],
    }

    log(f"Body: {payload}")

    try:
        response = requests.post(ANTHROPIC_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
        log(f"Raw API response: {result}")

        result_content = extract_json(result["content"][0]["text"])
        log(f"Extracted content: {result_content}")
        parsed = json.loads(result_content)
        return parsed.get("tags", [])
    except requests.exceptions.RequestException as e:
        log_err(f"Request error: {e}")
        if hasattr(e, 'response') and e.response is not None:
            log_err(f"Response body: {e.response.text}")
        return []
    except json.JSONDecodeError as e:
        log_err(f"Failed to parse the response: {e}")
        return []
    except (KeyError, IndexError) as e:
        log_err(f"Wrong response from Claude: {e}")
        return []


previews_sliced = []
original_files: dict[str, str] = {}


def change_slices_to_skip(database):
    new_previews = []
    prev_count = 0

    global previews_sliced
    for p in previews_sliced:
        for preview in p:
            original_file = original_files[preview]
            prev_count += 1
            ai_types_attr: Union[aps.apsync.Attribute, str] = database.attributes.get_attribute_value(
                original_file,
                "AI-Types")
            if ai_types_attr and len(ai_types_attr) > 0:
                continue

            new_previews.append(preview)

    new_previews_sliced = [
        new_previews[i:i + images_per_request] for i in
        range(0, len(new_previews), images_per_request)]
    delta = prev_count - len(new_previews)
    if delta > 0:
        msg = f"Reduced previews by {delta}: from {prev_count} to {len(new_previews)}"
        log(msg)
        ap.UI().show_info("Skipped files", msg)
    previews_sliced = new_previews_sliced


def proceed_callback(database):
    proceed_dialog.close()
    skip_existing_tags = proceed_dialog.get_value("skip_existing_tags")
    if skip_existing_tags:
        change_slices_to_skip(database)

    def run():
        progress = ap.Progress(
            "Requesting AI tags", "Processing", infinite=False, show_loading_screen=True, cancelable=True)
        global start_time
        start_time = datetime.now()
        log(f"Started tagging {len(previews_sliced)} previews")
        progress.report_progress(0)
        for i, p in enumerate(previews_sliced):
            if progress.canceled:
                progress.finish()
                # ap.UI().navigate_to_folder(initial_folder)
                return
            retries = MAX_RETRIES
            response = None
            while retries > 0:
                retries -= 1
                response = get_claude_response_images(prompt, p)
                progress.report_progress((i + 1) / len(previews_sliced))
                log(response)
                if len(response) < len(p):
                    # ap.UI().navigate_to_folder(initial_folder)
                    ap.UI().show_error(
                        "Error",
                        f"Not all images were tagged [Received {len(response)}, requested {len(p)}], retrying {retries} more times")
                    log_err(
                        f"Not all images were tagged [Received {len(response)}, requested {len(p)}], retrying {retries} more times")
                    continue
                break

            if retries <= 0:
                # ap.UI().navigate_to_folder(initial_folder)
                ap.UI().show_error(
                    "Error", f"Not all files were tagged after {MAX_RETRIES} retries, aborting")
                return

            progress2 = ap.Progress("Updating tags", "Processing", infinite=False, show_loading_screen=True)
            for j, preview in enumerate(p):
                progress2.report_progress(j / len(p))
                tags = response[j]

                # Track all used tags to prevent duplicates across categories
                seen_tags = set()

                if tagger_settings.file_label_ai_types:
                    types = tags.get("types", [])
                    if "types_additional" in tags:
                        types += tags["types_additional"]
                    types_tags = aps.AttributeTagList()
                    for k, tag in enumerate(types):
                        types[k] = replace_tag(tag, all_variants["AI-Types"])
                        if types[k].lower() in seen_tags:
                            continue
                        seen_tags.add(types[k].lower())
                        new_tag = check_or_update_attribute(attributes[0], types[k], database)
                        types_tags.append(new_tag)

                    database.attributes.set_attribute_value(original_files[p[j]], "AI-Types", types_tags)

                if tagger_settings.file_label_ai_genres:
                    genres = tags.get("genres", [])
                    if "genres_additional" in tags:
                        genres += tags["genres_additional"]
                    genres_tags = aps.AttributeTagList()

                    for k, tag in enumerate(genres):
                        genres[k] = replace_tag(tag, all_variants["AI-Genres"])
                        if genres[k].lower() in seen_tags:
                            continue
                        seen_tags.add(genres[k].lower())
                        new_tag = check_or_update_attribute(attributes[1], genres[k], database)
                        genres_tags.append(new_tag)

                    database.attributes.set_attribute_value(original_files[p[j]], "AI-Genres", genres_tags)

                if tagger_settings.file_label_ai_objects:
                    objects = tags.get("objects", [])
                    objects_tags = aps.AttributeTagList()
                    for k, tag in enumerate(objects):
                        objects[k] = replace_tag(tag, all_variants["AI-Objects"])
                        if objects[k].lower() in seen_tags:
                            continue
                        seen_tags.add(objects[k].lower())
                        new_tag = check_or_update_attribute(attributes[2], objects[k], database)
                        objects_tags.append(new_tag)

                    database.attributes.set_attribute_value(original_files[p[j]], "AI-Objects", objects_tags)
            progress2.finish()

        progress.finish()
        finish_time = datetime.now()
        log(f"Finished tagging in {finish_time - start_time}")
        # ap.UI().navigate_to_folder(initial_folder)

    ctx.run_async(run)


previews = []
file_input_paths = []
last_index = -1
generating_previews_count = 0
generating_previews_progress: Optional[ap.Progress] = None
cancel_generating_previews = False  # hack
ctx: Optional[ap.Context] = None
start_time = datetime.now()
previews_start_time = datetime.now()


def proceed_generating_previews(workspace_id, database, output_folder):
    if cancel_generating_previews:
        return
    if generating_previews_progress.canceled:
        return
    if generating_previews_count > len(file_input_paths):
        return

    if generating_previews_count == len(file_input_paths):
        finish_generating_previews(previews, database)
        return

    if last_index >= len(file_input_paths) - 1:
        return

    input_path = file_input_paths[last_index + 1]
    generate_preview_async(workspace_id, input_path, output_folder, database)


def generate_previews(workspace_id, input_paths, database):
    if len(input_paths) == 0:
        # ap.UI().navigate_to_folder(initial_folder)
        ap.UI().show_error("No supported files selected", "Please select files to tag")
        log_err("No supported files selected")
        return

    global previews_start_time
    previews_start_time = datetime.now()
    log(f"Started generating previews for {len(input_paths)} files")

    # start progress
    global generating_previews_progress
    generating_previews_progress = ap.Progress(
        "Generating previews", "Processing", infinite=False,
        show_loading_screen=True,
        cancelable=True)

    output_folder = create_temp_directory()

    global previews
    previews = []
    global file_input_paths
    file_input_paths = input_paths
    log("Output folder: {}".format(output_folder.replace("\\", "\\\\")))
    # start generating first 10 previews
    for i in range(min(images_per_request, len(input_paths))):
        input_path = input_paths[i]
        ctx.run_async(generate_preview_async, workspace_id, input_path, output_folder, database)


def generate_preview_async(workspace_id, input_path, output_folder, database):
    global last_index
    if last_index >= len(file_input_paths) - 1:
        return
    last_index += 1
    global cancel_generating_previews
    if cancel_generating_previews:
        return
    image_path = get_preview_image(workspace_id, input_path, output_folder)
    if not image_path == "":
        previews.append(image_path)
        original_files[image_path] = input_path

    global generating_previews_count
    generating_previews_count += 1
    log(f"Progress cancelled: {generating_previews_progress.canceled}")
    if generating_previews_progress.canceled:
        cancel_generating_previews = True
        generating_previews_progress.finish()
        # ap.UI().navigate_to_folder(initial_folder)
        return

    generating_previews_progress.report_progress(generating_previews_count / len(file_input_paths))
    proceed_generating_previews(workspace_id, database, output_folder)


def finish_generating_previews(input_paths, database):
    if generating_previews_progress.canceled:
        return
    generating_previews_progress.finish()
    log(f"Finished generating previews for {len(input_paths)} files")
    current_time = datetime.now()
    log(f"Generated {len(input_paths)} previews in {current_time - previews_start_time}")
    if len(input_paths) == 0:
        # ap.UI().navigate_to_folder(initial_folder)
        ap.UI().show_error("No supported files selected", "Please select files to tag")
        log_err("No supported files selected")
        return
    process_images(input_paths, database)


max_dimension = 128


def process_images(input_paths, database):
    # calculate pixel count
    pixel_count = 0
    asset_names = []
    progress = ap.Progress("Calculating pixel count", "Processing", infinite=False, show_loading_screen=True)
    for i, preview_path in enumerate(previews):
        [width, height] = resize_image(preview_path, max_dimension)
        pixel_count += width * height
        progress.report_progress(i / len(previews))
        asset_names.append(os.path.basename(original_files[preview_path]))

    global previews_sliced
    # slice previews by images_per_request
    previews_sliced = [previews[i:i + images_per_request] for i in range(0, len(previews), images_per_request)]

    # calculate token count (images are counted as tokens by Anthropic)
    image_tokens = len(previews) * IMAGE_TOKENS_ESTIMATE
    log(f"Pixel count: {pixel_count}")
    log(f"Estimated image tokens: {image_tokens}")
    progress.finish()
    token_prompts = count_tokens(prompt + schema_prompt) * len(previews_sliced)
    token_count = count_tokens(", ".join(asset_names))
    total_tokens = token_prompts + token_count + image_tokens
    combined_output_tokens = len(previews_sliced) * output_token_count

    total_price = total_tokens * INPUT_TOKEN_PRICE + combined_output_tokens * OUTPUT_TOKEN_PRICE

    req_count = len(previews_sliced)
    not_none_attr = len(attributes) - attributes.count(None)
    attr_count = len(input_paths) * not_none_attr

    data = CreateTagFilesDialogData(
        input_paths, total_tokens, combined_output_tokens, pixel_count, total_price,
        req_count, attr_count
    )
    global proceed_dialog
    proceed_dialog = create_tag_files_dialog(data, lambda d: proceed_callback(database))
    proceed_dialog.show()


attributes = []

ignored_extensions = extensions_without_preview


def get_all_files_recursive(folder_path) -> list[str]:
    files = []
    for root, _, file_names in os.walk(folder_path):
        for file_name in file_names:
            files.append(str(os.path.join(root, file_name)))

    return files


initial_folder = ""


def main():
    if not tagger_settings.any_file_tags_selected():
        ap.UI().show_error("No tags selected", "Please select at least one tag type in the settings")
        return

    global ctx
    ctx = ap.get_context()
    database = ap.get_api()
    # Create or get the "AI Tags" attributes
    types_attribute = ensure_attribute(database, "AI-Types") if tagger_settings.file_label_ai_types else None
    genres_attribute = ensure_attribute(database, "AI-Genres") if tagger_settings.file_label_ai_genres else None
    objects_attribute = ensure_attribute(database, "AI-Objects") if tagger_settings.file_label_ai_objects else None

    global attributes
    attributes = [types_attribute, genres_attribute, objects_attribute]

    selected_files = ctx.selected_files

    selected_folders = ctx.selected_folders

    log(selected_folders)

    if len(selected_folders) > 0:
        for folder in selected_folders:
            inner_files = get_all_files_recursive(folder)
            log(inner_files)
            selected_files.extend(inner_files)

    filtered_files = filter_ignored_extensions(selected_files, ignored_extensions)

    global initial_folder
    initial_folder = os.path.dirname(ctx.path)
    log(f"Initial folder: {initial_folder}")

    ctx.run_async(generate_previews, ctx.workspace_id, filtered_files, database)
    return


if __name__ == "__main__":
    main()
