import json

from labels.variants import engines_enum, types_enum, genres_enum


def get_folder_properties() -> dict:
    items = {
        "type": "object",
        "required": [],
        "properties": {}
    }
    from common.settings import tagger_settings

    if tagger_settings.folder_use_ai_types:
        items["required"].append("types")
        items["properties"]["types"] = {
            "type": "array",
            "items": {"type": "string", "enum": types_enum}
        }
        items["required"].append("types_additional")
        items["properties"]["types_additional"] = {
            "type": "array",
            "items": {"type": "string"}
        }

    if tagger_settings.folder_use_ai_engines:
        items["required"].append("engines")
        items["properties"]["engines"] = {
            "type": "array",
            "items": {"type": "string", "enum": engines_enum}
        }

    if tagger_settings.folder_use_ai_genres:
        items["required"].append("genres")
        items["properties"]["genres"] = {
            "type": "array",
            "items": {"type": "string", "enum": genres_enum}
        }
        items["required"].append("genres_additional")
        items["properties"]["genres_additional"] = {
            "type": "array",
            "items": {"type": "string"}
        }

    return items


def get_file_properties() -> dict:
    items = {
        "type": "object",
        "required": [],
        "properties": {}
    }
    from common.settings import tagger_settings

    if tagger_settings.file_label_ai_objects:
        items["required"].append("objects")
        items["properties"]["objects"] = {
            "type": "array",
            "items": {"type": "string"}
        }

    if tagger_settings.file_label_ai_types:
        items["required"].append("types")
        items["properties"]["types"] = {
            "type": "array",
            "items": {"type": "string", "enum": types_enum}
        }
        items["required"].append("types_additional")
        items["properties"]["types_additional"] = {
            "type": "array",
            "items": {"type": "string"}
        }

    if tagger_settings.file_label_ai_genres:
        items["required"].append("genres")
        items["properties"]["genres"] = {
            "type": "array",
            "items": {"type": "string", "enum": genres_enum}
        }
        items["required"].append("genres_additional")
        items["properties"]["genres_additional"] = {
            "type": "array",
            "items": {"type": "string"}
        }

    return items


def get_folder_schema_prompt(items) -> str:
    schema = {
        "type": "object",
        "required": ["items"],
        "properties": {
            "items": items
        }
    }
    return (
        "\n\nYou MUST respond with ONLY valid JSON matching this schema, no other text:\n"
        + json.dumps(schema, indent=2)
    )


def get_file_schema_prompt(items) -> str:
    schema = {
        "type": "object",
        "required": ["tags"],
        "properties": {
            "tags": {
                "type": "array",
                "items": items
            }
        }
    }
    return (
        "\n\nYou MUST respond with ONLY valid JSON matching this schema, no other text:\n"
        + json.dumps(schema, indent=2)
    )
