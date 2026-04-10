import json
import os
import random
from typing import Any

import anchorpoint as ap
import apsync as aps
import requests

from ai.api import init_anthropic_key, ANTHROPIC_API_URL, ANTHROPIC_API_VERSION, extract_json
from ai.constants import INPUT_TOKEN_PRICE, OUTPUT_TOKEN_PRICE, DEFAULT_MODEL
from ai.response_schema import get_folder_properties, get_folder_schema_prompt
from ai.tokens import count_tokens
from ap_tools.dialogs import CreateTagFoldersDialogData, create_tag_folders_dialog
from common.logging import log, log_err
from common.settings import tagger_settings
from labels.attributes import ensure_attribute, replace_tag, attribute_colors
from labels.variants import engines_variants, types_variants, genres_variants

prompt = ""
schema_prompt = ""


def build_prompts() -> tuple[str, str]:
    """Build the system prompt and JSON schema prompt from current settings.
    Called at the start of each invocation so that Settings changes take effect
    without restarting Anchorpoint."""
    p = "Write tags for the folder:"
    if tagger_settings.folder_use_ai_engines:
        p += "required game engines (e.g. UE if it has *.uasset or Unity if it has *.unitypackage) or 'Any' if assets have common types, "
    if tagger_settings.folder_use_ai_types:
        p += "content types (Texture, Sprite, Model, VFX, SFX, etc.) (min 1), "
    if tagger_settings.folder_use_ai_genres:
        p += "detailed genres (min 1), "
    p += "fill all tags"

    rules = tagger_settings.get_naming_rules()
    if rules:
        p += "\n\nCustom naming convention rules:\n" + rules

    sp = get_folder_schema_prompt(get_folder_properties())
    return p, sp


output_token_count = 200

proceed_dialog: ap.Dialog

all_variants = {
    "AI-Engines": engines_variants,
    "AI-Types": types_variants,
    "AI-Genres": genres_variants,
}


def get_folder_structure(input_path) -> dict[Any, list[Any]]:
    folder_structure = {}
    for root, dirs, files in os.walk(input_path):
        folder_structure[root] = files

    return folder_structure


def tag_folders(workspace_id: str, input_paths: list[str], database: aps.Api, attributes: list[aps.Attribute]):
    folders = []
    progress = ap.Progress("Counting tokens", "Processing", infinite=False, show_loading_screen=True)

    total_steps = 3
    for i, input_path in enumerate(input_paths):
        if os.path.isdir(input_path):
            folder_structure = get_folder_structure(input_path)
            progress.report_progress(i / len(input_paths) + (1 / total_steps / len(input_paths)))
            folder_structure_str = str(folder_structure)
            folder_name = os.path.basename(input_path)
            # replace input_path with "root"
            folder_structure_str = folder_structure_str.replace(input_path, "root")
            progress.report_progress(i / len(input_paths) + (2 / total_steps / len(input_paths)))
            log(folder_structure_str)

            full_prompt = f"{prompt}\nFolder name: {folder_name}\nFolder structure:\n{folder_structure_str}"
            log(full_prompt)
            token_count = count_tokens(full_prompt)
            progress.report_progress(i / len(input_paths) + (3 / total_steps / len(input_paths)))
            input_price = token_count * INPUT_TOKEN_PRICE
            folders.append((input_path, full_prompt, token_count, input_price))

    progress.finish()
    global proceed_dialog
    data = CreateTagFoldersDialogData(folders, output_token_count, OUTPUT_TOKEN_PRICE)
    proceed_dialog = create_tag_folders_dialog(
        data,
        lambda d: proceed_callback(folders, workspace_id, database, attributes))
    proceed_dialog.show()


def proceed_callback(
        folders: list[tuple[str, str, int, float]], workspace_id: str, database: aps.Api,
        attributes: list[aps.Attribute]):
    proceed_dialog.close()

    def run():
        progress = ap.Progress("Requesting AI tags", "Processing", infinite=False, show_loading_screen=True)
        progress.report_progress(0)
        for i, folder in enumerate(folders):
            tag_folder(folder[1], folder[0], workspace_id, database, attributes)
            progress.report_progress((i + 1) / len(folders))
        progress.finish()

    ctx = ap.get_context()
    ctx.run_async(run)


def get_claude_response(in_prompt, model=DEFAULT_MODEL) -> dict:
    headers = {
        "x-api-key": init_anthropic_key(),
        "anthropic-version": ANTHROPIC_API_VERSION,
        "Content-Type": "application/json"
    }

    payload = {
        "model": model,
        "max_tokens": 4096,
        "system": "You are a folder tagging AI." + schema_prompt,
        "messages": [
            {"role": "user", "content": in_prompt}
        ],
    }

    log(f"Body: {payload}")

    try:
        response = requests.post(ANTHROPIC_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
        log(f"Raw API response: {result}")
        prompt_tokens = result["usage"]["input_tokens"]
        completion_tokens = result["usage"]["output_tokens"]
        log(f"Input tokens: {prompt_tokens}, Output tokens: {completion_tokens}")
        result_content = extract_json(result["content"][0]["text"])
        log(f"Extracted content: {result_content}")
        parsed = json.loads(result_content)
        return parsed["items"]
    except requests.exceptions.RequestException as e:
        error_body = ""
        if hasattr(e, 'response') and e.response is not None:
            error_body = e.response.text
        log_err(f"Request error: {e} {error_body}")
        return {"error": str(e)}
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        log_err(f"Response parse error: {e}")
        return {"error": f"Wrong response from Claude: {e}"}


def tag_folder(
        full_prompt: str, input_path: str, workspace_id: str, database: aps.Api,
        attributes: list[aps.Attribute]):
    response = get_claude_response(full_prompt)
    log(response)
    if response.get("error"):
        err = f"Error while tagging folder: {response['error']}"
        ap.UI().show_error("Error", err)
        log_err(err)
        return

    tags = [
        response.get("engines", []) if tagger_settings.folder_use_ai_engines else None,
        (response.get("types", []) + response.get("types_additional", [])) if tagger_settings.folder_use_ai_types else None,
        (response.get("genres", []) + response.get("genres_additional", [])) if tagger_settings.folder_use_ai_genres else None
    ]

    if len(tags) != len(attributes):
        err = f"The number of categories ({len(tags)}) does not match the number of attributes ({len(attributes)})"
        ap.UI().show_error("Error", err)
        log_err(err)
        return

    for i, category_tags in enumerate(tags):
        if not category_tags:
            continue

        attribute = attributes[i]
        anchorpoint_tags = attribute.tags
        colors = attribute_colors

        # Names of tags already present in the attribute's vocabulary
        existing_tag_names = {a_tag.name for a_tag in anchorpoint_tags}

        # Canonicalize each raw tag via the variant table and dedup
        replaced_tags = []
        for raw_tag in category_tags:
            canonical = replace_tag(raw_tag.strip(), all_variants[attribute.name])
            if canonical and canonical not in replaced_tags:
                replaced_tags.append(canonical)

        # Extend the attribute's vocabulary with any new canonical tags
        for folder_tag in replaced_tags:
            if folder_tag not in existing_tag_names:
                new_tag = aps.AttributeTag(folder_tag, random.choice(colors))
                anchorpoint_tags.append(new_tag)

        # Update the attribute tags in the database
        database.attributes.set_attribute_tags(attribute, anchorpoint_tags)

        ao_tags = aps.AttributeTagList()
        for anchorpoint_tag in anchorpoint_tags:
            if anchorpoint_tag.name in replaced_tags:
                ao_tags.append(anchorpoint_tag)

        # Set the attribute value for the input path (skip empty to avoid
        # wiping existing tags when the AI returns nothing for this category)
        if len(ao_tags) > 0:
            database.attributes.set_attribute_value(input_path, attribute, ao_tags)


def main():
    if not tagger_settings.any_folder_tags_selected():
        ap.UI().show_error("No tags selected", "Please select at least one tag category in the settings")
        return

    global prompt, schema_prompt
    prompt, schema_prompt = build_prompts()

    ctx = ap.get_context()
    database = ap.get_api()

    engines_attribute = ensure_attribute(database, "AI-Engines") if tagger_settings.folder_use_ai_engines else None
    types_attribute = ensure_attribute(database, "AI-Types") if tagger_settings.folder_use_ai_types else None
    genres_attribute = ensure_attribute(database, "AI-Genres") if tagger_settings.folder_use_ai_genres else None

    attributes = [engines_attribute, types_attribute, genres_attribute]

    selected_folders = ctx.selected_folders
    if len(selected_folders) == 0:
        selected_folders = [ctx.path]

    ctx.run_async(
        tag_folders, ctx.workspace_id,
        selected_folders, database, attributes)


if __name__ == "__main__":
    main()
