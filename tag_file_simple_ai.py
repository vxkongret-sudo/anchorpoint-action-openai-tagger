import hashlib
import json
import os
from datetime import datetime
from typing import Any, Optional, Union

import anchorpoint as ap
import apsync as aps
import requests

from ai.api import init_anthropic_key, ANTHROPIC_API_URL, ANTHROPIC_API_VERSION, extract_json
from ai.constants import INPUT_TOKEN_PRICE, OUTPUT_TOKEN_PRICE, MAX_RETRIES, DEFAULT_MODEL
from ai.response_schema import get_file_properties, get_file_schema_prompt
from ai.tokens import count_tokens
from ap_tools.dialogs import CreateTagFilesDialogData, create_tag_files_dialog
from common.logging import log, log_err
from common.settings import tagger_settings
from labels.attributes import ensure_attribute, replace_tag, check_or_update_attribute
from labels.extensions import filter_ignored_extensions, junk_files_extensions
from labels.variants import types_variants, genres_variants, objects_variants

prompt = (
    "You are a file tagging AI. When asked, write tags for each file in the order they were presented: "
)

if tagger_settings.file_label_ai_types:
    prompt += "content types (Texture, Sprite, Model, VFX, SFX, etc.) (min 1),"

if tagger_settings.file_label_ai_genres:
    prompt += "detailed genres (min 1),"

if tagger_settings.file_label_ai_objects:
    prompt += f"objects and other keywords (min {tagger_settings.file_label_ai_objects_min}, max {tagger_settings.file_label_ai_objects_max}), "

prompt += "fill all tags for each file. Use Capitalized Words. IMPORTANT: Never repeat the same tag across different categories — each tag value must appear only once total."

naming_rules = tagger_settings.get_naming_rules()
if naming_rules:
    prompt += "\n\nCustom naming convention rules:\n" + naming_rules

ctx: Optional[ap.Context] = None
start_time = datetime.now()
attributes = []

output_token_count = 200

files_per_request = 10
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


ANTHROPIC_API_KEY = init_anthropic_key()


def get_claude_response_files(in_prompt, file_paths: list[str], model=DEFAULT_MODEL) -> list[Any]:
    if len(file_paths) == 0 or len(file_paths) > files_per_request:
        raise ValueError(f"The number of files should be between 1 and {files_per_request}")

    from common.filename import clean_character_filename
    # Send full paths so the AI can use folder structure for tagging
    # Preprocess Ch_ filenames to strip animation states
    file_descriptions = [clean_character_filename(file_path).replace("\\", "/") for file_path in file_paths]

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
            {"role": "user", "content": "Please tag these files (use both the filename and folder path for context):\n" + "\n".join(file_descriptions)}
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


def change_slices_to_skip(database):
    new_files = []
    prev_count = 0
    global file_paths_sliced
    for i, f in enumerate(file_paths_sliced):
        skip_progress.report_progress(i / len(file_paths_sliced))
        for file in f:
            prev_count += 1
            ai_types_attr: Union[aps.apsync.Attribute, str] = database.attributes.get_attribute_value(
                file,
                "AI-Types")
            if ai_types_attr and len(ai_types_attr) > 0:
                continue

            new_files.append(file)

    new_files_sliced = [
        new_files[i:i + files_per_request] for i in
        range(0, len(new_files), files_per_request)]
    delta = prev_count - len(new_files)
    if delta > 0:
        msg = f"Reduced files by {delta}: from {prev_count} to {len(new_files)}"
        log(msg)
        ap.UI().show_info("Skipped files", msg)
    file_paths_sliced = new_files_sliced


skip_progress: ap.Progress


def proceed_callback(database):
    proceed_dialog.close()

    skip_existing_tags = proceed_dialog.get_value("skip_existing_tags")
    if skip_existing_tags:
        global skip_progress
        skip_progress = ap.Progress("Calculating files to skip", "Processing", infinite=False, show_loading_screen=True)
        change_slices_to_skip(database)
        skip_progress.finish()

    def run():
        progress = ap.Progress(
            "Requesting AI tags", "Processing", infinite=False, show_loading_screen=True, cancelable=True)
        global start_time
        start_time = datetime.now()
        log(f"Started tagging {len(file_paths_sliced)} files")
        progress.report_progress(0)
        for i, p in enumerate(file_paths_sliced):
            if progress.canceled:
                progress.finish()
                # ap.UI().navigate_to_folder(initial_folder)
                return
            retries = MAX_RETRIES
            response = []
            while retries > 0:
                retries -= 1
                response = get_claude_response_files(prompt, p)
                progress.report_progress((i + 1) / len(file_paths_sliced))
                log(response)
                if len(response) < len(p):
                    ap.UI().show_error(
                        "Error",
                        f"Not all files were tagged [Received {len(response)}, requested {len(p)}], retrying {retries} more times")
                    log_err(
                        f"Not all files were tagged [Received {len(response)}, requested {len(p)}], retrying {retries} more times")
                    continue
                break

            if retries <= 0:
                # ap.UI().navigate_to_folder(initial_folder)
                ap.UI().show_error(
                    "Error", f"Not all files were tagged after {MAX_RETRIES} retries, aborting")
                return

            progress2 = ap.Progress("Updating tags", "Processing", infinite=False, show_loading_screen=True)

            for j, file_path in enumerate(p):
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

                    database.attributes.set_attribute_value(file_path, "AI-Types", types_tags)

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

                    database.attributes.set_attribute_value(file_path, "AI-Genres", genres_tags)

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

                    database.attributes.set_attribute_value(file_path, "AI-Objects", objects_tags)
            progress2.finish()

        progress.finish()
        finish_time = datetime.now()
        log(f"Finished tagging in {finish_time - start_time}")
        # ap.UI().navigate_to_folder(initial_folder)

    ctx.run_async(run)


file_paths_sliced = []


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

    filtered_files = filter_ignored_extensions(selected_files, junk_files_extensions)

    global initial_folder
    initial_folder = os.path.dirname(ctx.path)
    log(f"Initial folder: {initial_folder}")

    ctx.run_async(process_files, filtered_files, database)
    return


def process_files(input_paths, database):
    global file_paths_sliced
    # slice file paths by files_per_request
    file_paths_sliced = [input_paths[i:i + files_per_request] for i in range(0, len(input_paths), files_per_request)]

    # calculate token count
    input_paths_base_names = [os.path.basename(file_path) for file_path in input_paths]
    log(input_paths_base_names)
    token_prompts = count_tokens(prompt + schema_prompt) * len(file_paths_sliced)
    token_count = count_tokens(", ".join(input_paths_base_names))
    total_tokens = token_prompts + token_count
    combined_output_tokens = len(file_paths_sliced) * output_token_count

    total_price = total_tokens * INPUT_TOKEN_PRICE + combined_output_tokens * OUTPUT_TOKEN_PRICE

    req_count = len(file_paths_sliced)
    not_none_attr = len(attributes) - attributes.count(None)
    attr_count = len(input_paths) * not_none_attr

    data = CreateTagFilesDialogData(
        input_paths, total_tokens, combined_output_tokens, 0, total_price,
        req_count, attr_count
    )
    global proceed_dialog
    proceed_dialog = create_tag_files_dialog(data, lambda d: proceed_callback(database))
    proceed_dialog.show()


if __name__ == "__main__":
    main()
