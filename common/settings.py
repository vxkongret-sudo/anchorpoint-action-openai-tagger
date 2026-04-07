import os

import apsync as aps

class TaggerSettings:
    def __init__(self):
        self.local_settings = aps.Settings("ht_ai_tagger")
        self.load()

    def get(self, key: str, default: object = "") -> object:
        return self.local_settings.get(key, default)

    def set(self, key: str, value: object):
        self.local_settings.set(key, value)

    anthropic_api_key: str
    naming_rules_file: str
    file_label_ai_types: bool
    file_label_ai_genres: bool
    file_label_ai_objects: bool
    file_label_ai_objects_min: int
    file_label_ai_objects_max: int
    folder_use_ai_engines: bool
    folder_use_ai_types: bool
    folder_use_ai_genres: bool
    debug_log: bool

    def get_naming_rules(self) -> str:
        """Read naming rules from the file path, if set and valid."""
        if not self.naming_rules_file or not os.path.isfile(self.naming_rules_file):
            return ""
        try:
            with open(self.naming_rules_file, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            return ""

    def any_file_tags_selected(self):
        return self.file_label_ai_types or self.file_label_ai_genres or self.file_label_ai_objects

    def any_folder_tags_selected(self):
        return self.folder_use_ai_engines or self.folder_use_ai_types or self.folder_use_ai_genres

    def load(self):
        self.anthropic_api_key = str(self.get("anthropic_api_key"))
        self.naming_rules_file = str(self.get("naming_rules_file"))
        self.file_label_ai_types = bool(self.get("file_label_ai_types", True))
        self.file_label_ai_genres = bool(self.get("file_label_ai_genres", True))
        self.file_label_ai_objects = bool(self.get("file_label_ai_objects", True))
        self.file_label_ai_objects_min = int(str(self.get("file_label_ai_objects_min", 1)))
        self.file_label_ai_objects_max = int(str(self.get("file_label_ai_objects_max", 5)))
        self.folder_use_ai_engines = bool(self.get("folder_use_ai_engines", True))
        self.folder_use_ai_types = bool(self.get("folder_use_ai_types", True))
        self.folder_use_ai_genres = bool(self.get("folder_use_ai_genres", True))
        self.debug_log = bool(self.get("debug_log", False))

    def store(self):
        self.set("anthropic_api_key", self.anthropic_api_key)
        self.set("naming_rules_file", self.naming_rules_file)
        self.set("file_label_ai_types", self.file_label_ai_types)
        self.set("file_label_ai_genres", self.file_label_ai_genres)
        self.set("file_label_ai_objects", self.file_label_ai_objects)
        self.set("file_label_ai_objects_min", self.file_label_ai_objects_min)
        self.set("file_label_ai_objects_max", self.file_label_ai_objects_max)
        self.set("folder_use_ai_engines", self.folder_use_ai_engines)
        self.set("folder_use_ai_types", self.folder_use_ai_types)
        self.set("folder_use_ai_genres", self.folder_use_ai_genres)
        self.set("debug_log", self.debug_log)
        self.local_settings.store()

tagger_settings = TaggerSettings()
