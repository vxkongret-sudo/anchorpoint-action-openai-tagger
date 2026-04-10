# This example demonstrates how to create a simple dialog in Anchorpoint
import sys
import tempfile
from datetime import timedelta

import anchorpoint as ap
import os

from common.settings import tagger_settings

APPDATA_PATH = os.getenv("APPDATA")


def open_dir_callback(dir_path: str):
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
    os.startfile(dir_path)


def delete_api_key_callback(dialog: ap.Dialog):
    tagger_settings.anthropic_api_key = ""
    dialog.set_value("anthropic_api_key", "")
    tagger_settings.store()


def apply_callback(dialog: ap.Dialog):
    anthropic_api_key = str(dialog.get_value("anthropic_api_key"))

    tagger_settings.anthropic_api_key = anthropic_api_key

    tagger_settings.naming_rules_file = str(dialog.get_value("naming_rules_file"))

    tagger_settings.file_label_ai_types = bool(dialog.get_value("file_label_ai_types"))
    tagger_settings.file_label_ai_genres = bool(dialog.get_value("file_label_ai_genres"))
    tagger_settings.file_label_ai_objects = bool(dialog.get_value("file_label_ai_objects"))

    tagger_settings.file_label_ai_objects_min = int(str(dialog.get_value("file_label_ai_objects_min")))
    tagger_settings.file_label_ai_objects_max = int(str(dialog.get_value("file_label_ai_objects_max")))

    tagger_settings.folder_use_ai_engines = bool(dialog.get_value("folder_use_ai_engines"))
    tagger_settings.folder_use_ai_types = bool(dialog.get_value("folder_use_ai_types"))
    tagger_settings.folder_use_ai_genres = bool(dialog.get_value("folder_use_ai_genres"))

    tagger_settings.debug_log = bool(dialog.get_value("debug_log"))

    tagger_settings.store()
    ap.UI().show_success("Settings Updated")
    dialog.close()


def main():
    # Create a dialog container
    dialog = ap.Dialog()
    dialog.title = "AI Tagging Settings"
    ctx = ap.get_context()
    if ctx.icon:
        dialog.icon = ctx.icon

    dialog.add_text("<b>Anthropic API Key</b>")

    try:
        anthropic_api_key = tagger_settings.anthropic_api_key
    except KeyError:
        anthropic_api_key = ""

    dialog.add_input(
        anthropic_api_key, var="anthropic_api_key", width=400, placeholder="sk-ant-api03-...",
        password=True).add_button("Delete", callback=delete_api_key_callback)
    dialog.add_info(
        "An API key is an identifier (similar to username and password), that<br>allows you to access the AI-cloud services from Anthropic. Create an<br>API key on <a href='https://console.anthropic.com/settings/keys'>the Anthropic website</a>. You will need to set up billing first.")

    dialog.start_section("Naming Convention Rules", folded=False)
    dialog.add_text("<b>Rules File Path</b>")
    try:
        naming_rules_file = tagger_settings.naming_rules_file
    except KeyError:
        naming_rules_file = ""
    dialog.add_input(
        naming_rules_file, var="naming_rules_file", width=400,
        placeholder="H:\\MyProject\\tagging_rules.md")
    rules_content = tagger_settings.get_naming_rules()
    if rules_content:
        line_count = len(rules_content.strip().splitlines())
        dialog.add_info(f"Rules file loaded: {line_count} lines")
    else:
        dialog.add_info("No rules file set, or file not found. Tagging will use default AI behavior.")
    dialog.add_info(
        "Point to a text/markdown file with your naming convention rules.<br>"
        "The AI will follow these rules when tagging files and folders.<br>"
        "Example: prefix meanings, character names, folder-to-tag mappings.")
    dialog.add_separator()
    dialog.end_section()

    dialog.start_section("File Settings", folded=False)
    dialog.add_checkbox(tagger_settings.file_label_ai_types, var="file_label_ai_types", text="Label Types")
    dialog.add_info("e.g. model, texture, sfx")
    dialog.add_checkbox(tagger_settings.file_label_ai_genres, var="file_label_ai_genres", text="Label Genres")
    dialog.add_info("e.g. casual, cyberpunk, steampunk")
    (
        dialog.add_checkbox(tagger_settings.file_label_ai_objects, var="file_label_ai_objects", text="Label Objects\t")
        .add_text("Count:")
        .add_input(str(tagger_settings.file_label_ai_objects_min), var="file_label_ai_objects_min", width=50)
        .add_text("-")
        .add_input(str(tagger_settings.file_label_ai_objects_max), var="file_label_ai_objects_max", width=50)
    )
    dialog.add_info("What's in the picture. For example, an axe, a car, a character")
    dialog.add_separator()
    dialog.end_section()

    dialog.start_section("Folder Settings", folded=False)
    dialog.add_info("This will check the content of the folder, including all subfolders")
    dialog.add_checkbox(tagger_settings.folder_use_ai_engines, var="folder_use_ai_engines", text="Label Engines")
    dialog.add_info("e.g. Unity, Unreal, Godot")
    dialog.add_checkbox(tagger_settings.folder_use_ai_types, var="folder_use_ai_types", text="Label Types")
    dialog.add_info("e.g. model, texture, sfx")
    dialog.add_checkbox(tagger_settings.folder_use_ai_genres, var="folder_use_ai_genres", text="Label Genres")
    dialog.add_info("e.g. casual, cyberpunk, steampunk")
    dialog.add_separator()
    dialog.end_section()

    debug_folded = not tagger_settings.debug_log
    dialog.start_section("Debugging", folded=debug_folded)
    dialog.add_checkbox(tagger_settings.debug_log, var="debug_log", text="Enable Extended Logging")
    dialog.add_info("Log additional information to the console (open with CTRL+SHIFT+P)")
    dialog.add_separator()
    previews_dir = os.path.join(tempfile.gettempdir(), "anchorpoint", "ai_tagger", "previews")
    dialog.add_button("Open previews location", callback=lambda d: open_dir_callback(previews_dir))
    previews_ap_dir = rf"{APPDATA_PATH}\Anchorpoint Software\Anchorpoint\metadata"
    dialog.add_button("Open AP previews location", callback=lambda d: open_dir_callback(previews_ap_dir))
    dialog.end_section()

    dialog.add_info(
        "Monitor your <a href='https://console.anthropic.com/settings/keys'>API keys</a> "
        "and <a href='https://console.anthropic.com/settings/billing'>current spending</a> on the "
        "Anthropic website. This<br> Action was created by <b>Hermesis Trismegistus</b>.If you like it, "
        "feel free to<br><a href='https://ko-fi.com/hermesistrismegistus'>make a donation.</a>")

    dialog.add_button("Apply", callback=apply_callback)

    dialog.show()


if __name__ == "__main__":
    main()
