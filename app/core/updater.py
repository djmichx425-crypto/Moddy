"""
Auto-aktualizacje Moddy.
Sprawdza GitHub Releases i pobiera nowy instalator.
"""
from __future__ import annotations
import os
import subprocess
import sys
import tempfile
import threading
from pathlib import Path
from typing import Callable

import requests


def _api_url() -> str:
    try:
        from ..version import GITHUB_REPO
    except ImportError:
        GITHUB_REPO = "michxgaming2123/moddy"
    return f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"


def _parse_version(tag: str) -> tuple[int, ...]:
    tag = tag.lstrip("v").split("-")[0]
    try:
        return tuple(int(x) for x in tag.split("."))
    except Exception:
        return (0,)


def _install_dir() -> Path:
    """Katalog w którym zainstalowana jest aktualna wersja Moddy."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent.parent.parent   # fallback dev


def check_for_update(timeout: int = 6) -> dict | None:
    """
    Zwraca info o nowej wersji lub None jeśli aktualna.
    {"version": str, "url": str, "notes": str}
    """
    try:
        try:
            from ..version import VERSION_TUPLE
        except ImportError:
            VERSION_TUPLE = (1, 0, 0)

        r = requests.get(_api_url(), timeout=timeout,
                         headers={"Accept": "application/vnd.github+json"})
        if r.status_code != 200:
            return None

        data   = r.json()
        tag    = data.get("tag_name", "")
        remote = _parse_version(tag)
        if remote <= VERSION_TUPLE:
            return None

        # Szukaj pliku *_Setup.exe w assets
        asset_url = None
        for asset in data.get("assets", []):
            if asset["name"].lower().endswith("_setup.exe"):
                asset_url = asset["browser_download_url"]
                break

        if not asset_url:
            return None

        return {
            "version": tag,
            "url":     asset_url,
            "notes":   data.get("body", ""),
        }
    except Exception:
        return None


def download_and_install(
    url: str,
    on_progress: Callable[[int, int], None] | None = None,
    on_done: Callable[[bool, str], None] | None = None,
):
    """
    Pobiera nowy Setup.exe i uruchamia go z flagą --update <katalog>.
    Nowy instalator nadpisze pliki bez pokazywania wizarda.
    """
    def _run():
        try:
            r = requests.get(url, stream=True, timeout=120)
            r.raise_for_status()
            total = int(r.headers.get("content-length", 0))

            # Zapisz do pliku tymczasowego
            fd, tmp_path = tempfile.mkstemp(suffix="_Moddy_Setup.exe")
            downloaded   = 0
            with os.fdopen(fd, "wb") as f:
                for chunk in r.iter_content(65536):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if on_progress:
                        on_progress(downloaded, total)

            if on_done:
                on_done(True, "Uruchamianie aktualizacji…")

            # Uruchom instalator w trybie cichej aktualizacji
            install_path = str(_install_dir())
            subprocess.Popen(
                [tmp_path, "--update", install_path],
                creationflags=subprocess.DETACHED_PROCESS,
            )

            import time
            time.sleep(2)
            sys.exit(0)   # zamknij stary Moddy

        except Exception as e:
            if on_done:
                on_done(False, f"Błąd: {e}")

    threading.Thread(target=_run, daemon=True).start()
