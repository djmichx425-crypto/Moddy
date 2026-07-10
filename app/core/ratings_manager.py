"""
System ocen modów.
Lokalny zapis w JSON + synchronizacja z serwerem Moddy.
"""
from __future__ import annotations
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

APPDATA      = Path(os.environ.get("APPDATA", "~"))
RATINGS_FILE = APPDATA / "moddy" / "ratings.json"


def _load() -> dict:
    if RATINGS_FILE.exists():
        try:
            with open(RATINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save(data: dict):
    RATINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(RATINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _key(source: str, mod_id: str) -> str:
    return f"{source}:{mod_id}"


# ── API ───────────────────────────────────────────────────────────────────────

def get_rating(source: str, mod_id: str) -> dict | None:
    """Zwraca lokalną ocenę {'stars': 4, 'comment': '...', 'date': '...'}."""
    return _load().get(_key(source, mod_id))


def set_rating(source: str, mod_id: str,
               stars: int, comment: str = "",
               mod_name: str = "") -> dict:
    """Zapisuje ocenę lokalnie i próbuje synchronizować z serwerem."""
    stars = max(1, min(5, stars))
    data  = _load()
    entry = {
        "stars":    stars,
        "comment":  comment.strip(),
        "mod_name": mod_name,
        "date":     datetime.now().isoformat()[:10],
    }
    data[_key(source, mod_id)] = entry
    _save(data)
    _sync_to_server(source, mod_id, stars, comment, mod_name)
    return entry


def delete_rating(source: str, mod_id: str):
    data = _load()
    data.pop(_key(source, mod_id), None)
    _save(data)


def all_ratings() -> dict:
    """Zwraca wszystkie oceny {klucz: entry}."""
    return _load()


def get_server_ratings(source: str, mod_id: str) -> dict:
    """
    Pobiera zagregowane oceny z serwera Moddy.
    Zwraca: {'average': 4.2, 'count': 17, 'distribution': {1:0, 2:1, ...}}
    """
    try:
        from ..auth.api_client import SERVER_URL
        import requests
        r = requests.get(
            f"{SERVER_URL}/ratings/{source}/{mod_id}", timeout=4)
        if r.ok:
            return r.json()
    except Exception:
        pass
    return {"average": 0.0, "count": 0,
            "distribution": {str(i): 0 for i in range(1, 6)}}


def _sync_to_server(source: str, mod_id: str,
                    stars: int, comment: str, mod_name: str):
    """Asynchronicznie wysyła ocenę na serwer (jeśli zalogowany)."""
    import threading
    def _send():
        try:
            from ..auth.api_client import SERVER_URL
            from ..auth.token_store import load_session
            import requests
            token, _ = load_session()
            if not token:
                return
            requests.post(
                f"{SERVER_URL}/ratings",
                json={"source": source, "mod_id": mod_id,
                      "stars": stars, "comment": comment,
                      "mod_name": mod_name},
                headers={"Authorization": f"Bearer {token}"},
                timeout=5,
            )
        except Exception:
            pass
    threading.Thread(target=_send, daemon=True).start()
