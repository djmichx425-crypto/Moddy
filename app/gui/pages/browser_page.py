"""
Przeglądarka zawartości Minecraft.
Kategorie: Mody, Modpacki, Datapacki, Texturepacki, Mapy, Schematy, Inne.
Źródła: Modrinth, CurseForge, Planet Minecraft.
"""
import tkinter as tk
import customtkinter as ctk
import threading
import requests

from ...api import modrinth, spiget
from ...api import curseforge as cf_api
from ...api import planet_minecraft as pmc_api
from ...core.mod_library import LIBRARY_DIR, add_mod, load_settings
from ..components.mod_card import ModCard


FREE_PAGE_SIZE    = 5
PREMIUM_PAGE_SIZE = 20

# ── Definicje kategorii ────────────────────────────────────────────────────────
#   modrinth_type  – wartość project_type dla Modrinth (None = niedostępne)
#   cf_class_id    – classId dla CurseForge (None = niedostępne)
#   pmc_category   – klucz kategorii dla Planet Minecraft (None = niedostępne)
#   sources        – lista dostępnych źródeł dla tej kategorii

CATEGORIES: list[dict] = [
    {
        "label": "🔧  Mody",
        "key":   "mod",
        "modrinth_type": "mod",
        "cf_class_id":   6,
        "pmc_category":  None,
        "sources":       ["modrinth", "curseforge"],
    },
    {
        "label": "🎒  Modpacki",
        "key":   "modpack",
        "modrinth_type": "modpack",
        "cf_class_id":   4471,
        "pmc_category":  None,
        "sources":       ["modrinth", "curseforge"],
    },
    {
        "label": "📦  Datapacki",
        "key":   "datapack",
        "modrinth_type": "datapack",
        "cf_class_id":   6945,
        "pmc_category":  "datapack",
        "sources":       ["modrinth", "curseforge", "planetmc"],
    },
    {
        "label": "🎨  Texturepacki",
        "key":   "resourcepack",
        "modrinth_type": "resourcepack",
        "cf_class_id":   12,
        "pmc_category":  "resourcepack",
        "sources":       ["modrinth", "curseforge", "planetmc"],
    },
    {
        "label": "🗺  Mapy",
        "key":   "map",
        "modrinth_type": None,
        "cf_class_id":   17,
        "pmc_category":  "map",
        "sources":       ["curseforge", "planetmc"],
    },
    {
        "label": "🏗  Schematy",
        "key":   "schematic",
        "modrinth_type": None,
        "cf_class_id":   None,
        "pmc_category":  "build",
        "sources":       ["planetmc"],
    },
    {
        "label": "✨  Inne",
        "key":   "shader",
        "modrinth_type": "shader",
        "cf_class_id":   6552,
        "pmc_category":  None,
        "sources":       ["modrinth", "curseforge"],
    },
]

SOURCE_LABELS = {
    "modrinth":  "Modrinth",
    "curseforge": "CurseForge",
    "planetmc":  "Planet MC",
}


def _cat_by_key(key: str) -> dict:
    for c in CATEGORIES:
        if c["key"] == key:
            return c
    return CATEGORIES[0]


class BrowserPage(ctk.CTkFrame):
    def __init__(self, parent, navigate, **kwargs):
        super().__init__(parent, corner_radius=0, fg_color="#1a1a1a", **kwargs)
        self._navigate      = navigate
        self._settings      = load_settings()
        self._loader        = ""
        self._game_version  = ""
        self._offset        = 0
        self._total         = 0
        self._source        = "modrinth"
        self._category_key  = "mod"
        self._search_after_id = None
        self._cards: list[ModCard] = []
        self._user_info: dict | None = None
        self._build()

    # ── build ─────────────────────────────────────────────────────────────────

    def _build(self):
        # ── Kategorie (zakładki) ──────────────────────────────────────────────
        cat_bar = ctk.CTkFrame(self, corner_radius=0, fg_color="#161616")
        cat_bar.pack(fill="x")

        self._cat_btns: dict[str, ctk.CTkButton] = {}
        for cat in CATEGORIES:
            b = ctk.CTkButton(
                cat_bar,
                text=cat["label"],
                height=32,
                width=108,
                corner_radius=0,
                fg_color="transparent",
                hover_color="#2a2a2a",
                font=ctk.CTkFont(size=11),
                command=lambda k=cat["key"]: self._on_cat_change(k),
            )
            b.pack(side="left")
            self._cat_btns[cat["key"]] = b

        # ── Pasek wyszukiwania ────────────────────────────────────────────────
        top = ctk.CTkFrame(self, corner_radius=0, fg_color="#222222")
        top.pack(fill="x")

        ctk.CTkLabel(top, text="🔍",
                     font=ctk.CTkFont(size=15)).pack(side="left", padx=(12, 4), pady=10)

        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", self._on_search_change)
        ctk.CTkEntry(top, textvariable=self._search_var,
                     placeholder_text="Szukaj…",
                     width=240, height=32).pack(side="left", padx=4, pady=10)

        # Źródła (dynamiczne – zależne od kategorii)
        self._source_frame = ctk.CTkFrame(top, fg_color="transparent")
        self._source_frame.pack(side="left", padx=8)

        self._source_var = tk.StringVar(value="modrinth")
        self._source_radios: dict[str, ctk.CTkRadioButton] = {}
        for src_key, src_label in SOURCE_LABELS.items():
            rb = ctk.CTkRadioButton(
                self._source_frame,
                text=src_label,
                variable=self._source_var,
                value=src_key,
                command=self._on_source_change,
                font=ctk.CTkFont(size=11),
            )
            rb.pack(side="left", padx=5)
            self._source_radios[src_key] = rb

        self._header_label = ctk.CTkLabel(
            top, text="",
            font=ctk.CTkFont(size=11), text_color="#888")
        self._header_label.pack(side="right", padx=12)

        self._premium_badge = ctk.CTkLabel(
            top, text="",
            font=ctk.CTkFont(size=10, weight="bold"), text_color="#FFD700")
        self._premium_badge.pack(side="right", padx=4)

        self._compat_only = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(top, text="✅ Tylko kompatybilne",
                        variable=self._compat_only,
                        font=ctk.CTkFont(size=10),
                        command=lambda: self._search(self._search_var.get())
                        ).pack(side="right", padx=8)

        ctk.CTkButton(top, text="📚 Biblioteka", width=100, height=30,
                      fg_color="#2a7a4a", hover_color="#1f5c37",
                      command=lambda: self._navigate(
                          "library", loader=self._loader,
                          game_version=self._game_version
                      )).pack(side="right", padx=6)

        # ── Status ────────────────────────────────────────────────────────────
        self._status = ctk.CTkLabel(
            self, text="",
            font=ctk.CTkFont(size=11), text_color="#888")
        self._status.pack(anchor="w", padx=16, pady=(6, 0))

        # ── Kafelki ───────────────────────────────────────────────────────────
        self._scroll = ctk.CTkScrollableFrame(
            self, corner_radius=0, fg_color="transparent")
        self._scroll.pack(fill="both", expand=True, padx=8, pady=4)
        self._scroll.columnconfigure(0, weight=1)

        # ── Paginacja ─────────────────────────────────────────────────────────
        pag = ctk.CTkFrame(self, fg_color="#222222")
        pag.pack(fill="x")
        self._prev_btn = ctk.CTkButton(
            pag, text="← Poprzednia", width=120, height=30,
            fg_color="#3a3a3a", hover_color="#555",
            command=self._prev_page, state="disabled")
        self._prev_btn.pack(side="left", padx=8, pady=6)
        self._page_label = ctk.CTkLabel(pag, text="", font=ctk.CTkFont(size=11))
        self._page_label.pack(side="left", expand=True)
        self._next_btn = ctk.CTkButton(
            pag, text="Następna →", width=120, height=30,
            fg_color="#3a3a3a", hover_color="#555",
            command=self._next_page, state="disabled")
        self._next_btn.pack(side="right", padx=8, pady=6)

        # Inicjalizuj UI kategorii po utworzeniu wszystkich widgetów
        self._update_cat_ui()

    # ── categories ────────────────────────────────────────────────────────────

    def _update_cat_ui(self):
        """Podświetl aktywną kategorię i aktualizuj dostępne źródła."""
        cat = _cat_by_key(self._category_key)
        avail = cat["sources"]

        for key, btn in self._cat_btns.items():
            active = key == self._category_key
            btn.configure(
                fg_color="#FF6B35" if active else "transparent",
                text_color="#ffffff" if active else "#aaaaaa",
            )

        # Pokaż tylko dostępne źródła dla tej kategorii
        for src_key, rb in self._source_radios.items():
            if src_key in avail:
                rb.pack(side="left", padx=5)
            else:
                rb.pack_forget()

        # Jeśli aktualne źródło niedostępne → przełącz na pierwsze dostępne
        if self._source not in avail:
            self._source = avail[0]
            self._source_var.set(self._source)

    def _on_cat_change(self, key: str):
        if key == self._category_key:
            return
        self._category_key = key
        self._offset = 0
        self._update_cat_ui()
        self._search(self._search_var.get())

    # ── show ──────────────────────────────────────────────────────────────────

    @property
    def _page_size(self) -> int:
        from ...auth.token_store import is_premium
        return PREMIUM_PAGE_SIZE if is_premium(self._user_info) else FREE_PAGE_SIZE

    def set_user(self, user_info: dict | None):
        self._user_info = user_info
        from ...auth.token_store import is_premium
        self._premium_badge.configure(
            text="✨ Premium" if is_premium(user_info) else "🔒 Free (5 wyników)")

    def on_show(self, loader: str = "", game_version: str = "", **_):
        changed = (loader != self._loader or game_version != self._game_version)
        if changed:
            self._loader       = loader
            self._game_version = game_version
            self._offset       = 0
            self._search_var.set("")

        ldr_text = f"{loader.capitalize()} {game_version}" if loader else "wszystkie"
        self._header_label.configure(
            text=f"🎮 {ldr_text}",
            text_color="#FF6B35" if loader else "#888")

        self._settings = load_settings()
        self._search(self._search_var.get())

    # ── search / pagination ───────────────────────────────────────────────────

    def _on_search_change(self, *_):
        if self._search_after_id:
            self.after_cancel(self._search_after_id)
        self._search_after_id = self.after(
            400, lambda: self._search(self._search_var.get()))

    def _on_source_change(self):
        self._source = self._source_var.get()
        self._offset = 0
        self._search(self._search_var.get())

    def _search(self, query: str):
        self._source = self._source_var.get()
        self._status.configure(text="Wyszukiwanie…")
        threading.Thread(
            target=self._fetch, args=(query, self._offset), daemon=True).start()

    def _fetch(self, query: str, offset: int):
        cat    = _cat_by_key(self._category_key)
        src    = self._source
        ps     = self._page_size
        results: list[dict] = []
        total  = 0

        try:
            if src == "modrinth":
                mtype = cat["modrinth_type"]
                if mtype is None:
                    self.after(0, lambda: self._status.configure(
                        text="⚠ Modrinth nie obsługuje tej kategorii"))
                    self.after(0, lambda: self._render([], offset))
                    return
                data = modrinth.search(
                    query, self._loader, self._game_version,
                    ps, offset, project_type=mtype)
                total = data.get("total_hits", 0)
                for h in data.get("hits", []):
                    results.append({
                        "source":         "modrinth",
                        "id":             h.get("project_id", h.get("slug")),
                        "name":           h.get("title", ""),
                        "description":    h.get("description", ""),
                        "icon_url":       h.get("icon_url"),
                        "downloads":      h.get("downloads", 0),
                        "latest_version": (h.get("versions") or [""])[-1],
                        "slug":           h.get("slug"),
                    })

            elif src == "curseforge":
                class_id = cat["cf_class_id"]
                if class_id is None:
                    self.after(0, lambda: self._status.configure(
                        text="⚠ CurseForge nie obsługuje tej kategorii"))
                    self.after(0, lambda: self._render([], offset))
                    return
                key = self._settings.get("curseforge_api_key", "")
                if not key:
                    self.after(0, lambda: self._status.configure(
                        text="⚠ Brak klucza CurseForge – ustaw w Ustawieniach"))
                    return
                data = cf_api.search(
                    key, query, self._loader, self._game_version,
                    ps, offset, class_id=class_id)
                items = data.get("data", [])
                total = data.get("pagination", {}).get("totalCount", len(items))
                for m in items:
                    logo = m.get("logo") or {}
                    results.append({
                        "source":         "curseforge",
                        "id":             m.get("id"),
                        "name":           m.get("name", ""),
                        "description":    m.get("summary", ""),
                        "icon_url":       logo.get("thumbnailUrl"),
                        "downloads":      m.get("downloadCount", 0),
                        "latest_version": "",
                        "cf_data":        m,
                    })

            elif src == "planetmc":
                pmc_cat = cat["pmc_category"]
                if pmc_cat is None:
                    self.after(0, lambda: self._status.configure(
                        text="⚠ Planet Minecraft nie obsługuje tej kategorii"))
                    self.after(0, lambda: self._render([], offset))
                    return
                items = pmc_api.search(query, pmc_cat, limit=ps)
                total = len(items) + (1 if len(items) == ps else 0)
                results = items

            elif src == "spiget":
                items = spiget.search(query, ps, offset)
                total = 9999
                for r in items:
                    icon = r.get("icon", {})
                    has_icon = icon.get("data") or icon.get("url")
                    results.append({
                        "source":         "spiget",
                        "id":             r.get("id"),
                        "name":           r.get("name", ""),
                        "description":    r.get("tag", ""),
                        "icon_url":       spiget.get_icon_url(r["id"]) if has_icon else None,
                        "downloads":      r.get("downloads", 0),
                        "latest_version": r.get("version", {}).get("id", ""),
                    })

        except Exception as e:
            msg = str(e)
            self.after(0, lambda m=msg: self._status.configure(text=f"Błąd: {m}"))
            return

        self._total = total
        self.after(0, lambda: self._render(results, offset))

    def _render(self, results: list, offset: int):
        for w in self._scroll.winfo_children():
            w.destroy()
        self._cards.clear()

        if not results:
            ctk.CTkLabel(self._scroll, text="Brak wyników",
                         font=ctk.CTkFont(size=14),
                         text_color="#666").grid(row=0, column=0, pady=40)
        else:
            from ...core.mod_library import load_meta
            meta = load_meta()
            library_ids = {str(v.get("mod_id", "")) for v in meta.values()}

            for i, mod in enumerate(results):
                card = ModCard(
                    self._scroll, mod,
                    on_download=self._handle_download,
                    on_info=lambda m, cr=None: self._navigate(
                        "detail", mod_data=m, compat_result=cr),
                    loader=self._loader,
                    game_version=self._game_version,
                    settings=self._settings,
                    library_mod_ids=library_ids,
                )
                card.grid(row=i, column=0, sticky="ew", padx=4, pady=4)
                self._cards.append(card)

        ps = self._page_size
        page  = offset // ps + 1
        pages = max(1, -(-self._total // ps))
        self._page_label.configure(
            text=f"Strona {page} / {pages}  ({self._total} wyników)")
        self._prev_btn.configure(state="normal" if offset > 0 else "disabled")
        self._next_btn.configure(
            state="normal" if offset + ps < self._total else "disabled")

        cat_label = _cat_by_key(self._category_key)["label"].split("\xa0")[-1].strip()
        self._status.configure(
            text=f"{len(results)} wyników  •  {cat_label}  •  {SOURCE_LABELS.get(self._source, self._source)}")

    def _prev_page(self):
        self._offset = max(0, self._offset - self._page_size)
        self._search(self._search_var.get())

    def _next_page(self):
        self._offset += self._page_size
        self._search(self._search_var.get())

    # ── download ──────────────────────────────────────────────────────────────

    def _handle_download(self, mod_data: dict, anim):
        anim.start()
        threading.Thread(
            target=self._download_mod, args=(mod_data, anim), daemon=True).start()

    def _download_mod(self, mod_data: dict, anim):
        src = mod_data["source"]
        try:
            LIBRARY_DIR.mkdir(parents=True, exist_ok=True)

            if src == "modrinth":
                versions = modrinth.get_versions(
                    mod_data["id"], self._loader, self._game_version)
                if not versions:
                    versions = modrinth.get_versions(mod_data["id"])
                if not versions:
                    raise Exception("Brak plików dla tej wersji")
                file_info = versions[0]["files"][0]
                url, filename = file_info["url"], file_info["filename"]

            elif src == "curseforge":
                key = self._settings.get("curseforge_api_key", "")
                files = cf_api.get_files(key, mod_data["id"], self._game_version)
                if not files:
                    raise Exception("Brak plików")
                f = files[0]
                url      = f.get("downloadUrl")
                filename = f.get("fileName", f"cf_{mod_data['id']}.jar")

            elif src == "planetmc":
                url  = mod_data.get("url", "")
                if not url:
                    raise Exception("Brak URL do pobrania")
                # Planet MC – otwórz stronę (brak bezpośredniego linka do pliku)
                import webbrowser
                webbrowser.open(url)
                self.after(0, anim.finish)
                return

            elif src == "spiget":
                url = spiget.get_download_url(mod_data["id"])
                filename = (
                    f"spiget_{mod_data['id']}_"
                    f"{mod_data['name'].replace(' ', '_')}.jar"
                )
            else:
                raise Exception("Nieznane źródło")

            dest = LIBRARY_DIR / filename
            r = requests.get(url, stream=True, timeout=30,
                             headers={"User-Agent": "moddy/1.0"})
            r.raise_for_status()
            total = int(r.headers.get("Content-Length", 0))
            done  = 0
            with open(dest, "wb") as fh:
                for chunk in r.iter_content(8192):
                    fh.write(chunk)
                    done += len(chunk)
                    if total:
                        self.after(0, lambda v=done / total: anim.set_progress(v))

            add_mod(filename, {
                "name":         mod_data.get("name"),
                "source":       src,
                "mod_id":       str(mod_data.get("id")),
                "loader":       self._loader,
                "game_version": self._game_version,
                "download_url": url,
            })
            from ...core.integrity_checker import register_file
            register_file(filename)
            self.after(0, anim.finish)

        except Exception as e:
            msg = str(e)
            self.after(0, anim.reset)
            self.after(0, lambda m=msg: self._status.configure(
                text=f"Błąd pobierania: {m}"))
