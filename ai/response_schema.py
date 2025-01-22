from labels.variants import engines_enum, types_enum, genres_enum

engines_property = {
    "type": "array",
    "items": {
        "type": "string",
        "additionalProperties": False,
        "enum": engines_enum
    }
}

types_property = {
    "type": "array",
    "items": {
        "type": "string",
        "enum": types_enum,
        "additionalProperties": False,
    },
}

additional_types_property = {
    "type": "array",
    "items": {
        "type": "string",
        "additionalProperties": False,
    }
}

genres_property = {
    "type": "array",
    "items": {
        "type": "string",
        "enum": genres_enum,
        "additionalProperties": False,
    }
}

additional_genres_property = {
    "type": "array",
    "items": {
        "type": "string",
        "additionalProperties": False,
    }
}


def get_folder_properties() -> dict:
    items = {
        "type": "object",
        "additionalProperties": False,
        "required": [],
        "properties": {}
    }
    from common.settings import tagger_settings

    if tagger_settings.folder_use_ai_types:
        items["required"].append("types")
        items["properties"]["types"] = types_property
        items["required"].append("types_additional")
        items["properties"]["types_additional"] = additional_types_property

    if tagger_settings.folder_use_ai_engines:
        items["required"].append("engines")
        items["properties"]["engines"] = engines_property

    if tagger_settings.folder_use_ai_genres:
        items["required"].append("genres")
        items["properties"]["genres"] = genres_property
        items["required"].append("genres_additional")
        items["properties"]["genres_additional"] = additional_genres_property

    return items


def get_file_properties() -> dict:
    items = {
        "type": "object",
        "additionalProperties": False,
        "required": [],
        "properties": {}

    }
    from common.settings import tagger_settings

    if tagger_settings.file_label_ai_objects:
        items["required"].append("objects")
        items["properties"]["objects"] = {
            "type": "array",
            "items": {
                "type": "string",
                "additionalProperties": False,
            }
        }

    if tagger_settings.file_label_ai_types:
        items["required"].append("types")
        items["properties"]["types"] = types_property
        items["required"].append("types_additional")
        items["properties"]["types_additional"] = additional_types_property

    if tagger_settings.file_label_ai_genres:
        items["required"].append("genres")
        items["properties"]["genres"] = genres_property
        items["required"].append("genres_additional")
        items["properties"]["genres_additional"] = additional_genres_property

    return items


def get_folder_response_format(items):
    return {"type": "json_schema", "json_schema":
        {
            "name": "TaggingSchema",
            "strict": True,
            "schema": {
                "type": "object",
                "additionalProperties": False,
                "required": ["items"],
                "properties": {
                    "items": items
                },
                "name": "TaggingSchema"
            }
        }}


def get_file_response_format(items):
    return {"type": "json_schema", "json_schema":
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
