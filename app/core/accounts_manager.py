"""
Zarządzanie kontami Minecraft.
Obsługuje konta offline (bez weryfikacji) i Microsoft (OAuth2).
"""
import json
import os
import uuid
from pathlib import Path

APPDATA = Path(os.environ.get("APPDATA", "~"))
ACCOUNTS_FILE = APPDATA / "moddy" / "accounts.json"


def _load() -> dict:
    if ACCOUNTS_FILE.exists():
        try:
            with open(ACCOUNTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"accounts": [], "selected": None}


def _save(data: dict):
    ACCOUNTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(ACCOUNTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_accounts() -> list[dict]:
    return _load()["accounts"]


def get_selected_account() -> dict | None:
    data = _load()
    sel_uuid = data.get("selected")
    accounts = data["accounts"]
    if not accounts:
        return None
    if sel_uuid:
        for acc in accounts:
            if acc["uuid"] == sel_uuid:
                return acc
    return accounts[0]


def rename_account(acc_uuid: str, new_name: str) -> bool:
    """Zmienia nazwę konta offline. Zwraca True jeśli OK."""
    new_name = new_name.strip()
    if len(new_name) < 3:
        return False
    data = _load()
    for acc in data["accounts"]:
        if acc["uuid"] == acc_uuid:
            acc["username"] = new_name
            _save(data)
            return True
    return False


def add_offline_account(username: str) -> dict:
    username = username.strip()
    if not username:
        raise ValueError("Nazwa użytkownika nie może być pusta")
    if len(username) < 3:
        raise ValueError("Nazwa min. 3 znaki")
    data = _load()
    # Sprawdź czy już istnieje
    for acc in data["accounts"]:
        if acc["username"].lower() == username.lower() and acc["type"] == "offline":
            data["selected"] = acc["uuid"]
            _save(data)
            return acc
    acc = {
        "uuid": str(uuid.uuid4()),
        "username": username,
        "type": "offline",
        "token": "0",
    }
    data["accounts"].append(acc)
    data["selected"] = acc["uuid"]
    _save(data)
    return acc


def add_microsoft_account(username: str, player_uuid: str, token: str,
                          refresh_token: str = "") -> dict:
    """Dodaj konto Microsoft (po udanym OAuth)."""
    data = _load()
    # Aktualizuj jeśli istnieje
    for acc in data["accounts"]:
        if acc.get("uuid") == player_uuid:
            acc.update(username=username, token=token, refresh_token=refresh_token,
                       type="microsoft")
            data["selected"] = player_uuid
            _save(data)
            return acc
    acc = {
        "uuid": player_uuid,
        "username": username,
        "type": "microsoft",
        "token": token,
        "refresh_token": refresh_token,
    }
    data["accounts"].append(acc)
    data["selected"] = player_uuid
    _save(data)
    return acc


def remove_account(acc_uuid: str):
    data = _load()
    data["accounts"] = [a for a in data["accounts"] if a["uuid"] != acc_uuid]
    if data.get("selected") == acc_uuid:
        data["selected"] = data["accounts"][0]["uuid"] if data["accounts"] else None
    _save(data)


def set_selected(acc_uuid: str):
    data = _load()
    data["selected"] = acc_uuid
    _save(data)
