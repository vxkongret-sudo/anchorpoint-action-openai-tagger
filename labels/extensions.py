import os

from common.logging import log

unity_extensions = [
    "meta", "unity", "prefab", "asset", "mat", "controller", "anim", "mask",
    "overrideController", "physicMaterial", "physicsMaterial2D", "renderTexture", "shader",
    "cubemap", "flare", "giparams", "lightingData", "unitypackage", "cs", "asmdef", "asmref"
]

unreal_extensions = [
    "umap", "uplugin", "uproject", "uexp", "upk", "udk", "uc", "u", "udata", "uclass",
    "ustruct", "ufunction", "uinterface", "uenum", "uproperty"
]

roblox_extensions = [
    "rbxl", "rbxlx"
]

godot_extensions = [
    "tscn", "tres", "import", "scn", "res", "gd", "gdc", "gdscript", "gdn", "cfg", "json", "gdns"
]

engines = unity_extensions + unreal_extensions + roblox_extensions + godot_extensions

temp_extensions = [
    "tmp", "temp", "bak", "backup", "old", "cache", "log", "lock", "swp", "dmp", "err"
]

audio_extensions = [
    "mp3", "wav", "ogg", "flac", "aiff", "aif", "wma", "m4a", "aac", "mid", "midi", "mod", "xm", "it", "s3m", "flp",
    "opus", "amr"
]

text_extensions = [
    "txt", "md", "markdown", "rtf", "doc", "docx", "pdf", "odt", "tex", "log", "cfg", "ini"
]

archive_extensions = [
    "zip", "rar", "7z", "tar", "gz", "bz2", "xz", "iso", "cab", "dmg", "pkg"
]

script_extensions = [
    "py", "rb", "js", "ts", "sh", "bat", "ps1", "java", "cpp", "h", "c", "cs", "go", "lua"
]

data_extensions = [
    "csv", "json", "xml", "yaml", "yml", "sqlite", "db", "sql", "dat", "dbf", "parquet", "hdf5"
]

code_project_extensions = [
    "sln", "csproj", "vcxproj", "xcodeproj", "makefile", "cmake", "gradle",
]

extensions_without_preview = (
    engines
    + temp_extensions
    + audio_extensions
    + text_extensions
    + archive_extensions
    + script_extensions
    + data_extensions
    + code_project_extensions
)

junk_files_extensions = temp_extensions + archive_extensions + [
    "meta", "import", "orig", "rej", "undo", "redo", "autosave", "autosaved", "restore",
    "save", "sav", "log1", "log2", "journal", "pid", "tgz", "zst",
    "bak1", "bak2", "tmp1", "tmp2", "old1", "old2", "cache1", "cache2",
    "icns", "ico", "crash", "trace", "out",
    "aux", "bak~", "part", "crdownload", "download", "working", "gitkeep", "gitattributes",
    "lockfile", "npmignore", "editorconfig", "eslintignore", "prettierrc", "eslintrc"
]

# Full-filename matches (case-insensitive) for system junk that isn't cleanly
# a single extension. These catch things like .DS_Store / Thumbs.db / desktop.ini
# without over-filtering real .db or .ini files.
_junk_filenames = {
    ".ds_store",
    "thumbs.db",
    "desktop.ini",
}


def filter_ignored_extensions(files: list[str], ignored_ext: list[str]) -> list[str]:
    """Filter files whose extension is in ignored_ext, whose basename matches a
    known junk filename, or which have no extension. Comparison is case-insensitive."""
    ignored_set = {ext.lower() for ext in ignored_ext}
    filtered_files = []
    for file in files:
        basename = os.path.basename(file)
        lower = basename.lower()
        if lower in _junk_filenames:
            log(f"Ignoring file because of filename: {basename}")
            continue
        if "." not in basename:
            log(f"Ignoring file because of no extension: {basename}")
            continue
        file_ext = lower.rsplit(".", 1)[-1]
        if not file_ext:
            log(f"Ignoring file because of empty extension: {basename}")
            continue
        if file_ext in ignored_set:
            log(f"Ignoring file because of extension: {basename}")
            continue
        filtered_files.append(file)
    return filtered_files
