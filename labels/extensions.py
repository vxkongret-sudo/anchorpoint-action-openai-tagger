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

engines = unity_extensions + unreal_extensions + roblox_extensions + godot_extensions + roblox_extensions

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

extensions_without_preview = engines + [
    temp_extensions, audio_extensions,
    text_extensions, archive_extensions, script_extensions,
    data_extensions, code_project_extensions
]
