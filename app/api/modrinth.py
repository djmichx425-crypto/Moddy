import requests
from typing import Optional

BASE = "https://api.modrinth.com/v2"
HEADERS = {"User-Agent": "moddy/1.0 (minecraft-mod-manager)"}


def search(query: str, loader: Optional[str] = None, version: Optional[str] = None,
           limit: int = 20, offset: int = 0, project_type: str = "mod") -> dict:
    facets = [[f"project_type:{project_type}"]]
    if loader and project_type in ("mod", "modpack"):
        facets.append([f"categories:{loader.lower()}"])
    if version and project_type != "modpack":
        facets.append([f"versions:{version}"])

    import json
    params = {
        "query": query,
        "limit": limit,
        "offset": offset,
        "facets": json.dumps(facets),
    }
    r = requests.get(f"{BASE}/search", params=params, headers=HEADERS, timeout=10)
    r.raise_for_status()
    return r.json()


def get_project(project_id: str) -> dict:
    r = requests.get(f"{BASE}/project/{project_id}", headers=HEADERS, timeout=10)
    r.raise_for_status()
    return r.json()


def get_versions(project_id: str, loader: Optional[str] = None, game_version: Optional[str] = None) -> list:
    params = {}
    if loader:
        params["loaders"] = f'["{loader.lower()}"]'
    if game_version:
        params["game_versions"] = f'["{game_version}"]'
    r = requests.get(f"{BASE}/project/{project_id}/version", params=params, headers=HEADERS, timeout=10)
    r.raise_for_status()
    return r.json()


def get_loaders() -> list:
    r = requests.get(f"{BASE}/tag/loader", headers=HEADERS, timeout=10)
    r.raise_for_status()
    return [l["name"] for l in r.json() if l.get("supported_project_types") and "mod" in l["supported_project_types"]]


def get_game_versions() -> list:
    r = requests.get(f"{BASE}/tag/game_version", headers=HEADERS, timeout=10)
    r.raise_for_status()
    return [v["version"] for v in r.json() if v.get("version_type") == "release"]
