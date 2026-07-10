import requests
from typing import Optional

BASE = "https://api.curseforge.com/v1"
MINECRAFT_GAME_ID = 432


def _headers(api_key: str) -> dict:
    return {"x-api-key": api_key, "Accept": "application/json"}


CLASS_IDS: dict[str, int] = {
    "mod":         6,
    "modpack":     4471,
    "resourcepack": 12,
    "world":       17,
    "datapack":    6945,
    "shader":      6552,
}


def search(api_key: str, query: str, loader: Optional[str] = None,
           version: Optional[str] = None, limit: int = 20, offset: int = 0,
           class_id: int = 6) -> dict:
    LOADER_IDS = {"forge": 1, "fabric": 4, "quilt": 5, "neoforge": 6}
    params = {
        "gameId":       MINECRAFT_GAME_ID,
        "classId":      class_id,
        "searchFilter": query,
        "pageSize":     limit,
        "index":        offset,
        "sortField":    2,
        "sortOrder":    "desc",
    }
    if version:
        params["gameVersion"] = version
    if loader and loader.lower() in LOADER_IDS and class_id == 6:
        params["modLoaderType"] = LOADER_IDS[loader.lower()]

    r = requests.get(f"{BASE}/mods/search", params=params, headers=_headers(api_key), timeout=10)
    r.raise_for_status()
    return r.json()


def get_mod(api_key: str, mod_id: int) -> dict:
    r = requests.get(f"{BASE}/mods/{mod_id}", headers=_headers(api_key), timeout=10)
    r.raise_for_status()
    return r.json().get("data", {})


def get_files(api_key: str, mod_id: int, version: Optional[str] = None) -> list:
    params = {"pageSize": 10}
    if version:
        params["gameVersion"] = version
    r = requests.get(f"{BASE}/mods/{mod_id}/files", params=params, headers=_headers(api_key), timeout=10)
    r.raise_for_status()
    return r.json().get("data", [])
