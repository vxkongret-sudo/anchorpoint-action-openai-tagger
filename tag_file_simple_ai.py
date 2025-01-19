import hashlib
import json
import os
from datetime import datetime
from typing import Any, Optional

import anchorpoint as ap
import apsync as aps
import requests

from ai.api import init_openai_key, OPENAI_API_URL
from ai.constants import input_token_price, output_token_price
from ai.tokens import count_tokens
from ap_tools.dialogs import CreateTagFilesDialogData, create_tag_files_dialog
from common.logging import log, log_err
from common.settings import tagger_settings
from labels.attributes import ensure_attribute, replace_tag, check_or_update_attribute
from labels.extensions import unity_extensions, unreal_extensions, audio_extensions, temp_extensions, godot_extensions, \
    text_extensions
from labels.variants import types_variants, genres_variants, objects_variants

prompt = (
    "You are a file tagging AI. When asked, write tags for each file in the order they were presented: "
)

if tagger_settings.file_label_ai_types:
    prompt += "content types (Texture, Sprite, Model, VFX, SFX, etc.),"

if tagger_settings.file_label_ai_genres:
    prompt += "detailed genres,"

if tagger_settings.file_label_ai_objects:
    prompt += f"objects and other keywords (min {tagger_settings.file_label_ai_objects_min}, max {tagger_settings.file_label_ai_objects_max}), "

prompt += "fill all tags for each file."

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

items = {
    "type": "object",
    "additionalProperties": False,
    "required": [],
    "properties": {}
}

if tagger_settings.file_label_ai_types:
    items["required"].append("types")
    items["properties"]["types"] = {
        "type": "array",
        "items": {
            "type": "string",
            "additionalProperties": False,
        }
    }

if tagger_settings.file_label_ai_genres:
    items["required"].append("genres")
    items["properties"]["genres"] = {
        "type": "array",
        "items": {
            "type": "string",
            "additionalProperties": False,
        }
    }

if tagger_settings.file_label_ai_objects:
    items["required"].append("objects")
    items["properties"]["objects"] = {
        "type": "array",
        "items": {
            "type": "string",
            "additionalProperties": False,
        }
    }

response_format = {"type": "json_schema", "json_schema":
    {
        "name": "TaggingSchema",
        "strict": True,
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["tags"],
            "properties": {
                "tags": {
                    "type": "array",
                    "items": items
                }
            },
            "name": "TaggingSchema"
        }
    }}


def calculate_file_hash(file_path, hash_algorithm="sha256", length: int = 8):
    hash_func = hashlib.new(hash_algorithm)

    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            hash_func.update(chunk)

    return hash_func.hexdigest()[:length]


OPENAI_API_KEY = init_openai_key()


def get_openai_response_files(in_prompt, file_paths: list[str], model="gpt-4o-mini") -> list[Any]:
    if len(file_paths) == 0 or len(file_paths) > files_per_request:
        raise ValueError(f"The number of files should be between 1 and {files_per_request}")

    original_file_names = [os.path.basename(file_path) for file_path in file_paths]

    content = [{
        "type": "text",
        "text": "Please tag these files: " + ", ".join(original_file_names)
    }]

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": in_prompt},
            {"role": "user", "content": content}
        ],
        "response_format": response_format
    }

    log(f"Body: {payload}")

    try:
        response = requests.post(OPENAI_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()

        result_content = result["choices"][0]["message"]["content"].strip()
        parsed = json.loads(result_content)
        return parsed.get("tags", [])
    except requests.exceptions.RequestException as e:
        log_err(f"Request error: {e}")
        return []
    except json.JSONDecodeError:
        log_err("Failed to parse the response")
        return []


def proceed_callback(database):
    proceed_dialog.close()

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
                ap.UI().navigate_to_folder(initial_folder)
                return
            response = get_openai_response_files(prompt, p)
            progress.report_progress((i + 1) / len(file_paths_sliced))
            log(response)
            if len(response) < len(p):
                ap.UI().navigate_to_folder(initial_folder)
                ap.UI().show_error(
                    "Error", f"Not all files were tagged [Received {len(response)}, requested {len(p)}]")
                raise ValueError(f"Not all files were tagged [Received {len(response)}, requested {len(p)}]")

            progress2 = ap.Progress("Updating tags", "Processing", infinite=False, show_loading_screen=True)
            for j, file_path in enumerate(p):
                progress2.report_progress(j / len(p))
                tags = response[j]

                ap.UI().navigate_to_file(file_path)

                if tagger_settings.file_label_ai_types:
                    types = tags["types"]
                    types_tags = aps.AttributeTagList()
                    for k, tag in enumerate(types):
                        types[k] = replace_tag(tag, all_variants["AI-Types"])
                        new_tag = check_or_update_attribute(attributes[0], types[k], database)
                        types_tags.append(new_tag)

                    database.attributes.set_attribute_value(file_path, "AI-Types", types_tags)

                if tagger_settings.file_label_ai_genres:
                    genres = tags["genres"]
                    genres_tags = aps.AttributeTagList()

                    for k, tag in enumerate(genres):
                        genres[k] = replace_tag(tag, all_variants["AI-Genres"])
                        new_tag = check_or_update_attribute(attributes[1], genres[k], database)
                        genres_tags.append(new_tag)

                    database.attributes.set_attribute_value(file_path, "AI-Genres", genres_tags)

                if tagger_settings.file_label_ai_objects:
                    objects = tags["objects"]
                    objects_tags = aps.AttributeTagList()
                    for k, tag in enumerate(objects):
                        objects[k] = replace_tag(tag, all_variants["AI-Objects"])
                        new_tag = check_or_update_attribute(attributes[2], objects[k], database)
                        objects_tags.append(new_tag)

                    database.attributes.set_attribute_value(file_path, "AI-Objects", objects_tags)
            progress2.finish()

        progress.finish()
        finish_time = datetime.now()
        log(f"Finished tagging in {finish_time - start_time}")
        ap.UI().navigate_to_folder(initial_folder)

    ctx.run_async(run)


file_paths_sliced = []
original_files: dict[str, str] = {}


ignored_extensions = [
    unity_extensions, unreal_extensions, godot_extensions,
    temp_extensions, audio_extensions,
    text_extensions
]


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
        ap.UI().show_error(
            "Folders are experimental", "Please navigate inside the folder and change the view to List",
            60000)
        for folder in selected_folders:
            inner_files = get_all_files_recursive(folder)
            log(inner_files)
            selected_files.extend(inner_files)

    global initial_folder
    initial_folder = os.path.dirname(ctx.path)
    log(f"Initial folder: {initial_folder}")

    process_files(selected_files, database)
    return


def process_files(input_paths, database):
    global file_paths_sliced
    # slice file paths by images_per_request
    file_paths_sliced = [input_paths[i:i + files_per_request] for i in range(0, len(input_paths), files_per_request)]

    # calculate token count
    token_count = count_tokens(prompt + ", ".join(input_paths))
    total_tokens = token_count * len(file_paths_sliced)
    combined_output_tokens = len(input_paths) * output_token_count

    total_price = total_tokens * input_token_price + combined_output_tokens * output_token_price

    data = CreateTagFilesDialogData(input_paths, total_tokens, combined_output_tokens, 0, total_price)
    global proceed_dialog
    proceed_dialog = create_tag_files_dialog(data, lambda d: proceed_callback(database))
    proceed_dialog.show()


if __name__ == "__main__":
    main()
