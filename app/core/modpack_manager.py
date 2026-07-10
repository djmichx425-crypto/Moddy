"""
System paczek modów (fanowskich).
Format pliku: .modpack (JSON)

Schemat:
{
  "format":           "moddy-pack-1",
  "name":             "My Pack",
  "version":          "1.0.0",
  "description":      "Opis paczki",
  "author":           "Steve",
  "minecraft_version":"1.20.1",
  "loader":           "fabric",
  "loader_version":   null,
  "memory_mb":        2048,
  "mods": [
    {
      "name":         "Sodium",
      "source":       "modrinth",
      "mod_id":       "AANobbMI",
      "filename":     "sodium-0.5.8+mc1.20.1.jar",
      "download_url": "https://cdn.modrinth.com/…"
    }, …
  ],
  "created":          "2026-06-03T12:00:00",
  "moddy_version":    "2.0.0"
}
"""
import json
import os
import requests
import shutil
from datetime import datetime
from pathlib import Path
from typing import Callable

APPDATA      = Path(os.environ.get("APPDATA", "~"))
MODPACKS_DIR = APPDATA / "moddy" / "modpacks"
LIBRARY_DIR  = APPDATA / "moddy" / "library"
LIBRARY_META = APPDATA / "moddy" / "library_meta.json"

FORMAT_VERSION = "moddy-pack-1"


# ── I/O ───────────────────────────────────────────────────────────────────────

def list_modpacks() -> list[dict]:
    """Zwraca wszystkie paczki z katalogu modpacks/ (razem ze ścieżką)."""
    MODPACKS_DIR.mkdir(parents=True, exist_ok=True)
    packs = []
    for f in sorted(MODPACKS_DIR.glob("*.modpack")):
        try:
            with open(f, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            data["_path"] = str(f)
            packs.append(data)
        except Exception:
            pass
    return packs


def save_modpack(pack: dict) -> Path:
    """Zapisuje paczkę do pliku .modpack. Zwraca ścieżkę."""
    MODPACKS_DIR.mkdir(parents=True, exist_ok=True)
    safe = "".join(c for c in pack["name"] if c.isalnum() or c in " _-").strip()
    path = MODPACKS_DIR / f"{safe}.modpack"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(pack, f, indent=2, ensure_ascii=False)
    return path


def load_modpack_file(path: str | Path) -> dict:
    """Wczytuje paczkę z pliku .modpack."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def delete_modpack(path: str | Path):
    p = Path(path)
    if p.exists():
        p.unlink()


def export_modpack(pack: dict, dest_path: str | Path):
    """Kopiuje plik .modpack do wskazanej lokalizacji (dla użytkownika)."""
    src = Path(pack.get("_path", ""))
    if src.exists():
        shutil.copy2(src, dest_path)
    else:
        with open(dest_path, "w", encoding="utf-8") as f:
            clean = {k: v for k, v in pack.items() if not k.startswith("_")}
            json.dump(clean, f, indent=2, ensure_ascii=False)


# ── tworzenie paczki ──────────────────────────────────────────────────────────

def _load_meta() -> dict:
    if LIBRARY_META.exists():
        try:
            with open(LIBRARY_META, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def get_library_mods_for(loader: str, mc_version: str) -> list[dict]:
    """Zwraca mody z biblioteki pasujące do loadera i wersji MC."""
    meta = _load_meta()
    result = []
    for filename, info in meta.items():
        if (info.get("loader", "").lower() == loader.lower() and
                info.get("game_version") == mc_version):
            result.append({**info, "filename": filename})
    return result


def create_modpack(
    name: str,
    description: str,
    author: str,
    version: str,
    installation: dict,
    selected_mods: list[dict],
) -> dict:
    """
    Tworzy słownik paczki i zapisuje go do pliku.
    selected_mods – lista dict z kluczami: name, source, mod_id, filename, download_url
    """
    loader = installation.get("loader", "vanilla")
    mc_ver = installation.get("version") or installation.get("game_version", "")
    loader_ver = installation.get("loader_version")

    pack = {
        "format":            FORMAT_VERSION,
        "name":              name.strip() or "Moja paczka",
        "version":           version.strip() or "1.0.0",
        "description":       description.strip(),
        "author":            author.strip(),
        "minecraft_version": mc_ver,
        "loader":            loader,
        "loader_version":    loader_ver,
        "memory_mb":         installation.get("memory_mb", 2048),
        "mods":              selected_mods,
        "created":           datetime.now().isoformat(),
        "moddy_version":     "2.0.0",
    }
    save_modpack(pack)
    return pack


# ── instalacja paczki ─────────────────────────────────────────────────────────

def download_modpack_mods(
    pack: dict,
    instance_mods_dir: Path,
    settings: dict,
    on_status: Callable[[str], None] | None = None,
    on_progress: Callable[[float], None] | None = None,
) -> tuple[int, list[str]]:
    """
    Pobiera mody z paczki do instance_mods_dir.
    Zwraca (liczba_sukcesów, lista_błędów).
    """
    mods = pack.get("mods", [])
    instance_mods_dir.mkdir(parents=True, exist_ok=True)
    ok = 0
    errors = []

    for i, mod in enumerate(mods):
        name = mod.get("name", f"mod_{i}")
        if on_status:
            on_status(f"⬇ {name}  ({i + 1}/{len(mods)})")
        if on_progress:
            on_progress(i / max(len(mods), 1))

        url = mod.get("download_url")
        filename = mod.get("filename", f"mod_{i}.jar")

        # Jeśli nie ma URL — spróbuj odświeżyć ze źródła
        if not url:
            url = _resolve_url(mod, pack, settings)

        if not url:
            errors.append(f"{name}: brak URL pobierania")
            continue

        try:
            dest = instance_mods_dir / filename
            if dest.exists():
                ok += 1
                continue

            r = requests.get(url, stream=True, timeout=30,
                             headers={"User-Agent": "moddy-launcher/2.0"})
            r.raise_for_status()

            with open(dest, "wb") as f:
                for chunk in r.iter_content(8192):
                    if chunk:
                        f.write(chunk)
            ok += 1
        except Exception as e:
            errors.append(f"{name}: {e}")

    if on_progress:
        on_progress(1.0)
    return ok, errors


def _resolve_url(mod: dict, pack: dict, settings: dict) -> str | None:
    """Próbuje odświeżyć URL pobierania dla moda ze źródła."""
    src = mod.get("source", "")
    mod_id = mod.get("mod_id", "")
    mc_ver = pack.get("minecraft_version", "")
    loader = pack.get("loader", "")

    try:
        if src == "modrinth":
            from ..api import modrinth
            versions = modrinth.get_versions(mod_id, loader, mc_ver)
            if not versions:
                versions = modrinth.get_versions(mod_id)
            if versions:
                fi = versions[0]["files"][0]
                return fi["url"]

        elif src == "curseforge":
            from ..api import curseforge as cf
            key = settings.get("curseforge_api_key", "")
            if key:
                files = cf.get_files(key, mod_id, mc_ver)
                if files:
                    return files[0].get("downloadUrl")

        elif src == "spiget":
            from ..api import spiget
            return spiget.get_download_url(mod_id)

    except Exception:
        pass
    return None
