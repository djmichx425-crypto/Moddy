import tkinter as tk
import customtkinter as ctk
import threading
import requests
import os
from pathlib import Path
from typing import Optional

from ..api import modrinth, spiget
from ..api import curseforge as cf_api
from ..core.mod_library import LIBRARY_DIR, add_mod, load_settings
from .components.mod_card import ModCard
from .mod_detail import ModDetailWindow


class ModBrowser(ctk.CTkToplevel):
    PAGE_SIZE = 15

    def __init__(self, parent, loader: str, game_version: str, **kwargs):
        super().__init__(parent, **kwargs)
        self.loader = loader
        self.game_version = game_version
        self._settings = load_settings()
        self._offset = 0
        self._total = 0
        self._source = "modrinth"
        self._cards: list[ModCard] = []
        self._search_after_id = None

        self.title(f"Moddy – Przeglądarka modów ({loader} {game_version})")
        self.geometry("820x700")
        self.resizable(True, True)
        ctk.set_appearance_mode("dark")
        self._build_ui()
        self.after(100, lambda: self._search(""))

    def _build_ui(self):
        # top bar
        top = ctk.CTkFrame(self, corner_radius=0)
        top.pack(fill="x", padx=0, pady=0)

        ctk.CTkLabel(top, text="🔍", font=ctk.CTkFont(size=16)).pack(side="left", padx=(12, 4), pady=10)
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", self._on_search_change)
        self._search_entry = ctk.CTkEntry(top, textvariable=self._search_var,
                                          placeholder_text="Szukaj modów...",
                                          width=280, height=34)
        self._search_entry.pack(side="left", padx=4, pady=10)

        # source tabs
        self._source_var = tk.StringVar(value="modrinth")
        sources = [("Modrinth", "modrinth"), ("CurseForge", "curseforge"), ("SpigotMC", "spiget")]
        for label, val in sources:
            ctk.CTkRadioButton(top, text=label, variable=self._source_var, value=val,
                               command=self._on_source_change).pack(side="left", padx=8)

        # loader/version label
        ctk.CTkLabel(top, text=f"{self.loader} {self.game_version}",
                     font=ctk.CTkFont(size=11), text_color="#888").pack(side="right", padx=12)

        # status
        self._status_label = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=11),
                                          text_color="#888")
        self._status_label.pack(anchor="w", padx=16, pady=(6, 0))

        # scroll area for cards
        self._scroll = ctk.CTkScrollableFrame(self, corner_radius=0)
        self._scroll.pack(fill="both", expand=True, padx=10, pady=(4, 0))
        self._scroll.columnconfigure(0, weight=1)

        # pagination
        pag = ctk.CTkFrame(self, fg_color="transparent")
        pag.pack(fill="x", padx=10, pady=6)
        self._prev_btn = ctk.CTkButton(pag, text="← Poprzednia", width=120, height=30,
                                       fg_color="#3a3a3a", hover_color="#555",
                                       command=self._prev_page, state="disabled")
        self._prev_btn.pack(side="left")
        self._page_label = ctk.CTkLabel(pag, text="", font=ctk.CTkFont(size=11))
        self._page_label.pack(side="left", expand=True)
        self._next_btn = ctk.CTkButton(pag, text="Następna →", width=120, height=30,
                                       fg_color="#3a3a3a", hover_color="#555",
                                       command=self._next_page, state="disabled")
        self._next_btn.pack(side="right")

        # library button
        ctk.CTkButton(self, text="📦  Moja biblioteka", height=36,
                      fg_color="#2a7a4a", hover_color="#1f5c37",
                      command=self._open_library).pack(fill="x", padx=10, pady=(0, 8))

    # ── search / pagination ───────────────────────────────────────────────────

    def _on_search_change(self, *_):
        if self._search_after_id:
            self.after_cancel(self._search_after_id)
        self._search_after_id = self.after(400, lambda: self._search(self._search_var.get()))

    def _on_source_change(self):
        self._source = self._source_var.get()
        self._offset = 0
        self._search(self._search_var.get())

    def _search(self, query: str):
        self._source = self._source_var.get()
        self._status_label.configure(text="Wyszukiwanie...")
        threading.Thread(target=self._fetch, args=(query, self._offset), daemon=True).start()

    def _fetch(self, query: str, offset: int):
        results = []
        total = 0
        try:
            src = self._source
            if src == "modrinth":
                data = modrinth.search(query, self.loader, self.game_version,
                                       self.PAGE_SIZE, offset)
                total = data.get("total_hits", 0)
                for h in data.get("hits", []):
                    results.append({
                        "source": "modrinth",
                        "id": h.get("project_id", h.get("slug")),
                        "name": h.get("title", ""),
                        "description": h.get("description", ""),
                        "icon_url": h.get("icon_url"),
                        "downloads": h.get("downloads", 0),
                        "latest_version": (h.get("versions") or [""])[-1],
                        "slug": h.get("slug"),
                    })
            elif src == "curseforge":
                key = self._settings.get("curseforge_api_key", "")
                if not key:
                    self.after(0, lambda: self._status_label.configure(
                        text="⚠ Brak klucza CurseForge – ustaw go w Ustawieniach"))
                    return
                data = cf_api.search(key, query, self.loader, self.game_version,
                                     self.PAGE_SIZE, offset)
                items = data.get("data", [])
                total = data.get("pagination", {}).get("totalCount", len(items))
                for m in items:
                    logo = m.get("logo") or {}
                    results.append({
                        "source": "curseforge",
                        "id": m.get("id"),
                        "name": m.get("name", ""),
                        "description": m.get("summary", ""),
                        "icon_url": logo.get("thumbnailUrl"),
                        "downloads": m.get("downloadCount", 0),
                        "latest_version": "",
                        "cf_data": m,
                    })
            elif src == "spiget":
                items = spiget.search(query, self.PAGE_SIZE, offset)
                total = 9999
                for r in items:
                    icon = r.get("icon", {})
                    has_icon = icon.get("data") or icon.get("url")
                    results.append({
                        "source": "spiget",
                        "id": r.get("id"),
                        "name": r.get("name", ""),
                        "description": r.get("tag", ""),
                        "icon_url": spiget.get_icon_url(r["id"]) if has_icon else None,
                        "downloads": r.get("downloads", 0),
                        "latest_version": r.get("version", {}).get("id", ""),
                        "tested_versions": r.get("testedVersions", []),
                    })
        except Exception as e:
            self.after(0, lambda: self._status_label.configure(text=f"Błąd: {e}"))
            return

        self._total = total
        self.after(0, lambda: self._render_results(results, offset))

    def _render_results(self, results: list, offset: int):
        for w in self._scroll.winfo_children():
            w.destroy()
        self._cards.clear()

        if not results:
            ctk.CTkLabel(self._scroll, text="Brak wyników",
                         font=ctk.CTkFont(size=14), text_color="#666").grid(row=0, column=0, pady=40)
        else:
            for i, mod in enumerate(results):
                card = ModCard(self._scroll, mod,
                               on_download=self._handle_download,
                               on_info=self._show_detail)
                card.grid(row=i, column=0, sticky="ew", padx=4, pady=4)
                self._cards.append(card)

        page = offset // self.PAGE_SIZE + 1
        pages = max(1, -(-self._total // self.PAGE_SIZE))
        self._page_label.configure(text=f"Strona {page} / {pages}  ({self._total} wyników)")
        self._prev_btn.configure(state="normal" if offset > 0 else "disabled")
        self._next_btn.configure(state="normal" if offset + self.PAGE_SIZE < self._total else "disabled")
        self._status_label.configure(text=f"{len(results)} modów")

    def _prev_page(self):
        self._offset = max(0, self._offset - self.PAGE_SIZE)
        self._search(self._search_var.get())

    def _next_page(self):
        self._offset += self.PAGE_SIZE
        self._search(self._search_var.get())

    # ── download ──────────────────────────────────────────────────────────────

    def _handle_download(self, mod_data: dict, anim):
        anim.start()
        threading.Thread(target=self._download_mod, args=(mod_data, anim), daemon=True).start()

    def _download_mod(self, mod_data: dict, anim):
        try:
            src = mod_data["source"]
            LIBRARY_DIR.mkdir(parents=True, exist_ok=True)

            if src == "modrinth":
                versions = modrinth.get_versions(mod_data["id"], self.loader, self.game_version)
                if not versions:
                    versions = modrinth.get_versions(mod_data["id"])
                if not versions:
                    raise Exception("Brak dostępnych plików dla tej wersji")
                file_info = versions[0]["files"][0]
                url = file_info["url"]
                filename = file_info["filename"]

            elif src == "curseforge":
                key = self._settings.get("curseforge_api_key", "")
                files = cf_api.get_files(key, mod_data["id"], self.game_version)
                if not files:
                    raise Exception("Brak plików")
                f = files[0]
                url = f.get("downloadUrl")
                filename = f.get("fileName", f"mod_{mod_data['id']}.jar")

            elif src == "spiget":
                url = spiget.get_download_url(mod_data["id"])
                filename = f"spiget_{mod_data['id']}_{mod_data['name'].replace(' ', '_')}.jar"

            else:
                raise Exception("Nieznane źródło")

            dest = LIBRARY_DIR / filename
            r = requests.get(url, stream=True, timeout=30,
                             headers={"User-Agent": "moddy/1.0"})
            r.raise_for_status()
            total = int(r.headers.get("Content-Length", 0))
            downloaded = 0
            with open(dest, "wb") as f:
                for chunk in r.iter_content(8192):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        self.after(0, lambda v=downloaded / total: anim.set_progress(v))

            add_mod(filename, {
                "name": mod_data.get("name"),
                "source": src,
                "mod_id": str(mod_data.get("id")),
                "loader": self.loader,
                "game_version": self.game_version,
            })
            self.after(0, anim.finish)

        except Exception as e:
            self.after(0, anim.reset)
            self.after(0, lambda: self._status_label.configure(text=f"Błąd pobierania: {e}"))

    # ── detail / library ──────────────────────────────────────────────────────

    def _show_detail(self, mod_data: dict):
        ModDetailWindow(self, mod_data, self.loader, self.game_version)

    def _open_library(self):
        from .library_window import LibraryWindow
        LibraryWindow(self, self.loader, self.game_version)
