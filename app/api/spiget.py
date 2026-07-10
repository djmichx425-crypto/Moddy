import requests
from typing import Optional

BASE = "https://api.spiget.org/v2"
HEADERS = {"User-Agent": "moddy/1.0"}


def search(query: str, limit: int = 20, offset: int = 0) -> list:
    params = {"size": limit, "page": offset // limit + 1, "sort": "-downloads", "fields": "id,name,tag,icon,downloads,rating,version,testedVersions,description,links"}
    r = requests.get(f"{BASE}/search/resources/{requests.utils.quote(query)}", params=params, headers=HEADERS, timeout=10)
    r.raise_for_status()
    return r.json()


def get_resource(resource_id: int) -> dict:
    r = requests.get(f"{BASE}/resources/{resource_id}", headers=HEADERS, timeout=10)
    r.raise_for_status()
    return r.json()


def get_versions(resource_id: int) -> list:
    r = requests.get(f"{BASE}/resources/{resource_id}/versions", params={"size": 10, "sort": "-releaseDate"}, headers=HEADERS, timeout=10)
    r.raise_for_status()
    return r.json()


def get_icon_url(resource_id: int) -> str:
    return f"https://api.spiget.org/v2/resources/{resource_id}/icon"


def get_download_url(resource_id: int) -> str:
    return f"https://api.spiget.org/v2/resources/{resource_id}/download"
