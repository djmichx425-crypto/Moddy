import tkinter as tk
import customtkinter as ctk
import threading
import requests
from io import BytesIO
from PIL import Image, ImageTk

from .download_animation import DownloadAnimation
from ...core.compatibility_checker import (
    check_mod_async, CompatResult, STATUS_OK, STATUS_UNKNOWN
)
from ...core.ratings_manager import get_rating, set_rating, get_server_ratings


SOURCE_COLORS = {
    "modrinth":   "#1BD96A",
    "curseforge": "#F16436",
    "spiget":     "#1E88E5",
}


class ModCard(ctk.CTkFrame):
    def __init__(self, parent, mod_data: dict,
                 on_download=None, on_info=None,
                 loader: str = "", game_version: str = "",
                 settings: dict | None = None,
                 library_mod_ids: set | None = None,
                 **kwargs):
        super().__init__(parent, corner_radius=8, **kwargs)
        self.mod_data       = mod_data
        self.on_download    = on_download
        self.on_info        = on_info
        self._loader        = loader
        self._game_version  = game_version
        self._settings      = settings or {}
        self._library_ids   = library_mod_ids or set()
        self._icon_tk       = None
        self._compat_result: CompatResult | None = None
        self._build()
        self._load_icon_async()
        self._check_compat_async()

    # ── build ─────────────────────────────────────────────────────────────────

    def _build(self):
        self.columnconfigure(1, weight=1)

        # ikona / animacja
        self._anim = DownloadAnimation(self)
        self._anim.grid(row=0, column=0, rowspan=4, padx=(10, 8), pady=8, sticky="ns")

        # badge źródła
        source = self.mod_data.get("source", "")
        ctk.CTkLabel(self, text=source.upper(),
                     font=ctk.CTkFont(size=9, weight="bold"),
                     text_color=SOURCE_COLORS.get(source, "#aaa"),
                     fg_color="transparent").grid(
            row=0, column=1, sticky="w", padx=2, pady=(8, 0))

        # nazwa
        name = self.mod_data.get("name", "Unknown Mod")
        ctk.CTkLabel(self, text=name,
                     font=ctk.CTkFont(size=13, weight="bold"),
                     anchor="w", wraplength=300).grid(
            row=1, column=1, sticky="w", padx=2)

        # opis
        desc = self.mod_data.get("description", "")[:120]
        ctk.CTkLabel(self, text=desc,
                     font=ctk.CTkFont(size=11), text_color="#aaaaaa",
                     anchor="w", wraplength=300, justify="left").grid(
            row=2, column=1, sticky="w", padx=2, pady=(0, 4))

        # gwiazdki oceny
        stars_row = ctk.CTkFrame(self, fg_color="transparent")
        stars_row.grid(row=3, column=1, sticky="w", padx=2, pady=(2, 0))
        self._star_btns: list[ctk.CTkButton] = []
        for s in range(1, 6):
            btn = ctk.CTkButton(
                stars_row, text="☆", width=20, height=20,
                font=ctk.CTkFont(size=13),
                fg_color="transparent", hover_color="#2a2a2a",
                text_color="#666",
                command=lambda n=s: self._rate(n))
            btn.pack(side="left", padx=0)
            self._star_btns.append(btn)
        self._rating_lbl = ctk.CTkLabel(
            stars_row, text="", font=ctk.CTkFont(size=9), text_color="#555")
        self._rating_lbl.pack(side="left", padx=4)
        self._load_rating()

        # stats + compat badge w jednym rzędzie
        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.grid(row=4, column=1, sticky="w", pady=(0, 6))

        downloads = self.mod_data.get("downloads", 0)
        ctk.CTkLabel(bottom, text=f"⬇ {self._fmt(downloads)}",
                     font=ctk.CTkFont(size=10), text_color="#888").pack(
            side="left", padx=(0, 8))

        ver = self.mod_data.get("latest_version", "")
        if ver:
            ctk.CTkLabel(bottom, text=f"v{ver}",
                         font=ctk.CTkFont(size=10), text_color="#888").pack(
                side="left", padx=(0, 10))

        # badge kompatybilności — placeholder, aktualizowany po async check
        self._compat_badge = ctk.CTkLabel(
            bottom, text="❓ Sprawdzam…",
            font=ctk.CTkFont(size=10), text_color="#555")
        self._compat_badge.pack(side="left")

        # przyciski
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=0, column=2, rowspan=5, padx=10, pady=8, sticky="e")

        ctk.CTkButton(btn_frame, text="Info", width=65, height=28,
                      fg_color="#3a3a3a", hover_color="#555",
                      command=self._info_click).pack(pady=(0, 6))
        ctk.CTkButton(btn_frame, text="Pobierz", width=65, height=28,
                      fg_color="#FF6B35", hover_color="#e05520",
                      command=self._download_click).pack()

    # ── ratings ───────────────────────────────────────────────────────────────

    def _load_rating(self):
        src    = self.mod_data.get("source", "")
        mod_id = str(self.mod_data.get("id", ""))
        if not mod_id:
            return
        local = get_rating(src, mod_id)
        if local:
            self._update_stars(local["stars"], server_avg=None)
        # Pobierz ocenę serwera w tle
        import threading
        threading.Thread(target=self._fetch_server_rating,
                         args=(src, mod_id), daemon=True).start()

    def _fetch_server_rating(self, src: str, mod_id: str):
        data = get_server_ratings(src, mod_id)
        avg   = data.get("average", 0.0)
        count = data.get("count", 0)
        if count > 0:
            try:
                if self.winfo_exists():
                    self.after(0, lambda: self._update_stars(None, avg, count))
            except Exception:
                pass

    def _rate(self, stars: int):
        src     = self.mod_data.get("source", "")
        mod_id  = str(self.mod_data.get("id", ""))
        name    = self.mod_data.get("name", "")
        if not mod_id:
            return
        set_rating(src, mod_id, stars, mod_name=name)
        self._update_stars(stars, server_avg=None)

    def _update_stars(self, user_stars: int | None,
                      server_avg: float | None, count: int = 0):
        try:
            if not self.winfo_exists():
                return
        except Exception:
            return
        # Gwiazdki użytkownika
        for i, btn in enumerate(self._star_btns, start=1):
            if user_stars and i <= user_stars:
                btn.configure(text="★", text_color="#FFD700")
            else:
                btn.configure(text="☆", text_color="#555")
        # Etykieta z oceną serwera
        if server_avg and count:
            self._rating_lbl.configure(
                text=f"  {server_avg:.1f} ({count})",
                text_color="#888")
        elif not user_stars:
            self._rating_lbl.configure(text="oceń", text_color="#444")
        else:
            self._rating_lbl.configure(text="", text_color="#555")

    # ── compat ────────────────────────────────────────────────────────────────

    def _check_compat_async(self):
        """Uruchamia sprawdzanie kompatybilności w tle."""
        if not self._loader and not self._game_version:
            self._compat_badge.configure(text="", text_color="#555")
            return

        mod_id   = str(self.mod_data.get("id", ""))
        mod_name = self.mod_data.get("name", "")
        source   = self.mod_data.get("source", "")

        if not mod_id or source == "spiget":
            self._compat_badge.configure(text="❓ Brak danych", text_color="#555")
            return

        check_mod_async(
            mod_id=mod_id,
            mod_name=mod_name,
            source=source,
            loader=self._loader,
            mc_version=self._game_version,
            settings=self._settings,
            library_mod_ids=self._library_ids,
            callback=self._on_compat_result,
        )

    def _on_compat_result(self, result: CompatResult):
        self._compat_result = result
        try:
            if self.winfo_exists():
                self.after(0, lambda: self._update_compat_badge(result))
        except Exception:
            pass

    def _update_compat_badge(self, result: CompatResult):
        try:
            if not self.winfo_exists():
                return
            self._compat_badge.configure(
                text=result.short_label(),
                text_color=result.color())
        except Exception:
            pass

    def get_compat_result(self) -> CompatResult | None:
        return self._compat_result

    # ── icon ──────────────────────────────────────────────────────────────────

    def _load_icon_async(self):
        url = self.mod_data.get("icon_url")
        if url:
            threading.Thread(target=self._fetch_icon, args=(url,), daemon=True).start()

    def _fetch_icon(self, url: str):
        try:
            r = requests.get(url, timeout=5)
            r.raise_for_status()
            img = Image.open(BytesIO(r.content)).convert("RGBA").resize(
                (56, 56), Image.LANCZOS)
            self._icon_tk = ImageTk.PhotoImage(img)
            def _safe_set():
                try:
                    if self.winfo_exists() and self._anim.winfo_exists():
                        self._anim.set_icon(self._icon_tk)
                except Exception:
                    pass
            self.after(0, _safe_set)
        except Exception:
            pass

    # ── callbacks ─────────────────────────────────────────────────────────────

    def _download_click(self):
        if self.on_download:
            self.on_download(self.mod_data, self._anim)

    def _info_click(self):
        if self.on_info:
            self.on_info(self.mod_data, self._compat_result)

    def start_download_anim(self):   self._anim.start()
    def set_download_progress(self, v): self._anim.set_progress(v)
    def finish_download_anim(self):  self._anim.finish()

    @staticmethod
    def _fmt(n) -> str:
        try:
            n = int(n)
            if n >= 1_000_000: return f"{n/1_000_000:.1f}M"
            if n >= 1_000:     return f"{n/1_000:.0f}K"
            return str(n)
        except Exception:
            return str(n)
