import os
import json
import shutil
from pathlib import Path

APPDATA = Path(os.environ.get("APPDATA", "~"))
LIBRARY_DIR     = APPDATA / "moddy" / "library"
META_FILE       = APPDATA / "moddy" / "library_meta.json"
INSTALLATIONS_FILE = APPDATA / "moddy" / "installations.json"
SETTINGS_FILE   = APPDATA / "moddy" / "settings.json"
INSTANCES_DIR   = APPDATA / "moddy" / "instances"

# Stara ścieżka – fallback (nie używamy już globalnie)
MINECRAFT_MODS  = APPDATA / ".minecraft" / "mods"


def _safe_name(name: str) -> str:
    return "".join(c for c in name if c.isalnum() or c in " _-").strip() or "default"


def get_instance_mods_dir(installation: dict) -> Path:
    """Zwraca katalog mods dla konkretnej instalacji."""
    name = installation.get("name", "default")
    return INSTANCES_DIR / _safe_name(name) / "mods"


def ensure_dirs():
    LIBRARY_DIR.mkdir(parents=True, exist_ok=True)
    MINECRAFT_MODS.mkdir(parents=True, exist_ok=True)


def load_meta() -> dict:
    if META_FILE.exists():
        with open(META_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_meta(meta: dict):
    META_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(META_FILE, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)


def add_mod(filename: str, meta_info: dict) -> Path:
    ensure_dirs()
    dest = LIBRARY_DIR / filename
    meta = load_meta()
    meta[filename] = meta_info
    save_meta(meta)
    return dest


def list_mods() -> list[dict]:
    ensure_dirs()
    meta = load_meta()
    result = []
    for filepath in LIBRARY_DIR.iterdir():
        if filepath.suffix == ".jar":
            info = meta.get(filepath.name, {})
            info["filename"] = filepath.name
            info["path"] = str(filepath)
            result.append(info)
    return result


def remove_mod(filename: str):
    path = LIBRARY_DIR / filename
    if path.exists():
        path.unlink()
    meta = load_meta()
    meta.pop(filename, None)
    save_meta(meta)


def install_mod(filename: str, installation: dict | None = None) -> bool:
    """Kopiuje mod z biblioteki do katalogu mods instancji."""
    src = LIBRARY_DIR / filename
    if not src.exists():
        return False
    if installation:
        dest_dir = get_instance_mods_dir(installation)
    else:
        dest_dir = MINECRAFT_MODS
    dest_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest_dir / filename)
    return True


def load_installations() -> list:
    if INSTALLATIONS_FILE.exists():
        try:
            with open(INSTALLATIONS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []


def save_installations(installations: list):
    INSTALLATIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(INSTALLATIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(installations, f, indent=2, ensure_ascii=False)


def load_settings() -> dict:
    defaults = {
        "curseforge_api_key": "",
        "theme": "dark",
        "default_memory_mb": 2048,
        "java_path": "",
    }
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            defaults.update(data)
        except Exception:
            pass
    return defaults


def save_settings(settings: dict):
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)
