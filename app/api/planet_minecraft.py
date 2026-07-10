"""
Planet Minecraft – scraper wyników wyszukiwania.
Używa html.parser ze stdlib (brak zewnętrznych zależności).
"""
import re
from html.parser import HTMLParser
from typing import Optional

import requests

BASE = "https://www.planetminecraft.com"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

CATEGORY_PATHS: dict[str, str] = {
    "map":          "/resources/maps/",
    "resourcepack": "/resources/texture_packs/",
    "datapack":     "/resources/data_packs/",
    "mod":          "/resources/mods/",
    "build":        "/resources/builds/",
}

_RE_STRIP = re.compile(r"\s+")


class _PMCParser(HTMLParser):
    """Wyciąga kafelki zasobów z HTML Planet Minecraft."""

    def __init__(self):
        super().__init__()
        self.results: list[dict] = []
        self._cur: dict | None = None
        self._depth = 0
        self._cur_start_depth = 0
        self._grab_title = False
        self._grab_desc = False
        self._grab_count = False

    # ── tag open ──────────────────────────────────────────────────────────────

    def handle_starttag(self, tag: str, attrs):
        self._depth += 1
        a = dict(attrs)
        cls = a.get("class", "")

        # Nowy kafelek wyników
        if tag in ("li", "div") and (
            "r-info-block" in cls or "resource-block" in cls
            or "resource-list-block" in cls or "blockcell" in cls
        ):
            self._cur = {"source": "planetmc"}
            self._cur_start_depth = self._depth
            return

        if self._cur is None:
            return

        # Miniatura
        if tag == "img" and not self._cur.get("icon_url"):
            src = a.get("src") or a.get("data-src", "")
            if src and ("planetminecraft" in src or src.startswith("/")):
                if not src.startswith("http"):
                    src = BASE + src
                self._cur["icon_url"] = src

        # Link tytułowy
        if tag == "a" and not self._cur.get("url"):
            href = a.get("href", "")
            if "/resources/" in href and len(href) > 12:
                url = href if href.startswith("http") else BASE + href
                self._cur["url"] = url
                if "r-title" in a.get("class", ""):
                    self._grab_title = True

        if tag == "h2" and not self._cur.get("name"):
            self._grab_title = True

        if tag in ("p", "span") and "r-count" in cls:
            self._grab_count = True

    # ── tag close ─────────────────────────────────────────────────────────────

    def handle_endtag(self, tag: str):
        self._depth -= 1
        self._grab_title = False
        self._grab_desc = False
        self._grab_count = False

        if self._cur is not None and self._depth < self._cur_start_depth:
            if self._cur.get("name") and self._cur.get("url"):
                self.results.append(self._cur)
            self._cur = None

    # ── text ──────────────────────────────────────────────────────────────────

    def handle_data(self, data: str):
        data = _RE_STRIP.sub(" ", data).strip()
        if not data or self._cur is None:
            return
        if self._grab_title and not self._cur.get("name"):
            self._cur["name"] = data
        elif self._grab_count:
            digits = re.sub(r"[^\d]", "", data)
            if digits:
                self._cur["downloads"] = int(digits)


# ── public API ────────────────────────────────────────────────────────────────

def search(query: str, category: str = "map", limit: int = 10) -> list[dict]:
    """
    Wyszukuje zasoby na Planet Minecraft.
    Zwraca listę słowników kompatybilnych z formatem ModCard.
    """
    path = CATEGORY_PATHS.get(category, CATEGORY_PATHS["map"])
    params: dict = {"sort": "updated"}
    if query.strip():
        params["q"] = query.strip()

    try:
        resp = requests.get(
            BASE + path, params=params,
            headers=HEADERS, timeout=12,
        )
        resp.raise_for_status()
    except Exception:
        return []

    parser = _PMCParser()
    try:
        parser.feed(resp.text)
    except Exception:
        return []

    out: list[dict] = []
    for item in parser.results[:limit]:
        name = item.get("name", "")
        if not name:
            continue
        out.append({
            "source":         "planetmc",
            "id":             item.get("url", f"pmc_{len(out)}"),
            "name":           name,
            "description":    f"Planet Minecraft  –  {_label(category)}",
            "icon_url":       item.get("icon_url"),
            "downloads":      item.get("downloads", 0),
            "latest_version": "",
            "url":            item.get("url", ""),
        })

    return out


def _label(category: str) -> str:
    return {
        "map":          "Mapa",
        "resourcepack": "Texture Pack",
        "datapack":     "Data Pack",
        "mod":          "Mod",
        "build":        "Schemat/Build",
    }.get(category, category)
