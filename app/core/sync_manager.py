"""
Synchronizacja danych Premium (światy, screenshoty, ustawienia, historia).
Wymaga zalogowanego konta Moddy Premium.
"""
from __future__ import annotations
import json
import os
import shutil
import threading
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Callable

APPDATA        = Path(os.environ.get("APPDATA", "~"))
INSTANCES_DIR  = APPDATA / "moddy" / "instances"
MC_DIR         = APPDATA / ".minecraft"
BACKUP_DIR     = APPDATA / "moddy" / "backups"
HISTORY_DIR    = APPDATA / "moddy" / "history"
SETTINGS_FILE  = APPDATA / "moddy" / "settings.json"
INSTALLATIONS  = APPDATA / "moddy" / "installations.json"


# ── local history ─────────────────────────────────────────────────────────────

def save_config_snapshot(label: str = "") -> Path:
    """Zapisuje snapshot aktualnej konfiguracji (instalacje + ustawienia)."""
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    ts    = datetime.now().strftime("%Y%m%d_%H%M%S")
    name  = f"{ts}_{label or 'snapshot'}"
    snap  = HISTORY_DIR / f"{name}.json"
    data  = {
        "timestamp":     datetime.now().isoformat(),
        "label":         label or "Automatyczny snapshot",
        "installations": _read_json(INSTALLATIONS),
        "settings":      _read_json(SETTINGS_FILE),
    }
    snap.write_text(json.dumps(data, indent=2, ensure_ascii=False),
                    encoding="utf-8")
    return snap


def list_snapshots() -> list[dict]:
    """Zwraca listę snapshotów sortowaną od najnowszego."""
    if not HISTORY_DIR.exists():
        return []
    snaps = []
    for f in sorted(HISTORY_DIR.glob("*.json"), reverse=True):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            snaps.append({
                "path":      str(f),
                "timestamp": data.get("timestamp", ""),
                "label":     data.get("label", f.stem),
                "n_inst":    len(data.get("installations", [])),
            })
        except Exception:
            pass
    return snaps


def restore_snapshot(path: str) -> bool:
    """Przywraca konfigurację ze snapshotu."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if "installations" in data:
            _write_json(INSTALLATIONS, data["installations"])
        if "settings" in data:
            _write_json(SETTINGS_FILE, data["settings"])
        return True
    except Exception:
        return False


def delete_snapshot(path: str):
    p = Path(path)
    if p.exists():
        p.unlink()


# ── local backup ──────────────────────────────────────────────────────────────

def backup_world(instance_name: str, world_name: str) -> Path | None:
    """Zipuje świat i zapisuje w backups/."""
    world_dir = INSTANCES_DIR / _safe(instance_name) / "saves" / world_name
    if not world_dir.exists():
        return None
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = BACKUP_DIR / f"{_safe(instance_name)}_{_safe(world_name)}_{ts}.zip"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in world_dir.rglob("*"):
            zf.write(f, f.relative_to(world_dir.parent))
    return out


def list_worlds(instance_name: str) -> list[str]:
    saves = INSTANCES_DIR / _safe(instance_name) / "saves"
    if not saves.exists():
        return []
    return [d.name for d in saves.iterdir() if d.is_dir()]


def list_screenshots(instance_name: str) -> list[Path]:
    ss = INSTANCES_DIR / _safe(instance_name) / "screenshots"
    if not ss.exists():
        return []
    return sorted(ss.glob("*.png"), reverse=True)


# ── server sync ───────────────────────────────────────────────────────────────

def sync_to_server(
    token: str,
    sync_type: str,        # "worlds" | "screenshots" | "settings"
    instance_name: str = "",
    on_progress: Callable[[str], None] | None = None,
) -> tuple[bool, str]:
    """
    Wysyła dane na serwer Moddy.
    Zwraca (sukces, komunikat).
    """
    try:
        from ..auth.api_client import SERVER_URL
        import requests as req

        headers = {"Authorization": f"Bearer {token}"}

        if sync_type == "settings":
            data = {
                "installations": _read_json(INSTALLATIONS),
                "settings":      _read_json(SETTINGS_FILE),
            }
            r = req.post(f"{SERVER_URL}/sync/settings",
                         json=data, headers=headers, timeout=30)
            r.raise_for_status()
            return True, "Ustawienia zsynchronizowane"

        elif sync_type == "worlds" and instance_name:
            if on_progress:
                on_progress("Pakowanie światów…")
            worlds = list_worlds(instance_name)
            if not worlds:
                return False, "Brak światów do synchronizacji"
            for world in worlds:
                zip_path = backup_world(instance_name, world)
                if zip_path:
                    if on_progress:
                        on_progress(f"Wysyłanie {world}…")
                    with open(zip_path, "rb") as f:
                        r = req.post(
                            f"{SERVER_URL}/sync/worlds",
                            headers=headers,
                            files={"file": (zip_path.name, f, "application/zip")},
                            data={"instance": instance_name, "world": world},
                            timeout=120,
                        )
                        r.raise_for_status()
            return True, f"Zsynchronizowano {len(worlds)} światów"

        elif sync_type == "screenshots" and instance_name:
            shots = list_screenshots(instance_name)
            if not shots:
                return False, "Brak screenshotów"
            sent = 0
            for shot in shots[:50]:   # max 50
                if on_progress:
                    on_progress(f"Screenshot {shot.name}…")
                with open(shot, "rb") as f:
                    r = req.post(
                        f"{SERVER_URL}/sync/screenshots",
                        headers=headers,
                        files={"file": (shot.name, f, "image/png")},
                        data={"instance": instance_name},
                        timeout=30,
                    )
                    if r.ok:
                        sent += 1
            return True, f"Wysłano {sent} screenshotów"

        return False, "Nieznany typ synchronizacji"

    except Exception as e:
        return False, f"Błąd synchronizacji: {e}"


def sync_from_server(
    token: str,
    sync_type: str,
    instance_name: str = "",
    on_progress: Callable[[str], None] | None = None,
) -> tuple[bool, str]:
    """Pobiera dane z serwera."""
    try:
        from ..auth.api_client import SERVER_URL
        import requests as req

        headers = {"Authorization": f"Bearer {token}"}

        if sync_type == "settings":
            r = req.get(f"{SERVER_URL}/sync/settings",
                        headers=headers, timeout=15)
            r.raise_for_status()
            data = r.json()
            # Zapisz snapshot przed nadpisaniem
            save_config_snapshot("Przed sync z serwera")
            if "installations" in data:
                _write_json(INSTALLATIONS, data["installations"])
            if "settings" in data:
                _write_json(SETTINGS_FILE, data["settings"])
            return True, "Ustawienia przywrócone z chmury"

        return False, "Pobieranie nie jest jeszcze obsługiwane dla tego typu"

    except Exception as e:
        return False, f"Błąd pobierania: {e}"


# ── helpers ───────────────────────────────────────────────────────────────────

def _safe(name: str) -> str:
    return "".join(c for c in name if c.isalnum() or c in " _-").strip() or "default"


def _read_json(path: Path) -> dict | list:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False),
                    encoding="utf-8")
