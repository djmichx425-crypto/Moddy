import threading
import customtkinter as ctk

from ...core.mod_library import (
    list_mods, install_mod, remove_mod, MINECRAFT_MODS, load_settings
)
from ...core.compatibility_checker import (
    check_library, CompatResult, STATUS_OK, STATUS_WARN, STATUS_ERROR
)


class LibraryPage(ctk.CTkFrame):
    def __init__(self, parent, navigate, **kwargs):
        super().__init__(parent, corner_radius=0, fg_color="#1a1a1a", **kwargs)
        self._navigate = navigate
        self._loader = ""
        self._game_version = ""
        self._installation: dict | None = None
        self._compat_results: dict[str, CompatResult] = {}  # filename → result
        self._build()

    def _build(self):
        top = ctk.CTkFrame(self, fg_color="#222222", corner_radius=0)
        top.pack(fill="x")

        ctk.CTkLabel(top, text="📦  Biblioteka modów",
                     font=ctk.CTkFont(size=16, weight="bold")).pack(
            side="left", padx=14, pady=12)

        self._compat_btn = ctk.CTkButton(
            top, text="🔍 Sprawdź kompatybilność", height=30, width=190,
            fg_color="#2a2a5a", hover_color="#3a3a8a",
            font=ctk.CTkFont(size=11),
            command=self._run_compat_check)
        self._compat_btn.pack(side="right", padx=10, pady=10)

        self._header_label = ctk.CTkLabel(
            top, text="", font=ctk.CTkFont(size=11), text_color="#888")
        self._header_label.pack(side="right", padx=14)

        self._scroll = ctk.CTkScrollableFrame(
            self, corner_radius=0, fg_color="transparent")
        self._scroll.pack(fill="both", expand=True, padx=8, pady=4)
        self._scroll.columnconfigure(0, weight=1)

        bottom = ctk.CTkFrame(self, fg_color="#222222")
        bottom.pack(fill="x")

        self._status = ctk.CTkLabel(
            bottom, text="", font=ctk.CTkFont(size=11), text_color="#888")
        self._status.pack(side="left", padx=12, pady=8)

        ctk.CTkButton(bottom, text="✅  Zainstaluj wszystkie", height=34,
                      fg_color="#2a7a4a", hover_color="#1f5c37",
                      command=self._install_all).pack(side="right", padx=12, pady=8)

    # ── on_show ───────────────────────────────────────────────────────────────

    def on_show(self, loader: str = "", game_version: str = "",
                installation: dict | None = None, **_):
        self._loader = loader
        self._game_version = game_version
        self._installation = installation
        self._header_label.configure(
            text=f"{loader} {game_version}" if loader else "")
        self._compat_results.clear()
        self._refresh()

    # ── refresh ───────────────────────────────────────────────────────────────

    def _refresh(self):
        for w in self._scroll.winfo_children():
            w.destroy()

        mods = list_mods()
        if not mods:
            ctk.CTkLabel(self._scroll,
                         text="Biblioteka jest pusta.\nPobierz mody w Przeglądarce.",
                         font=ctk.CTkFont(size=13), text_color="#666",
                         justify="center").grid(row=0, column=0, pady=60)
            self._status.configure(text="0 modów")
            return

        for i, mod in enumerate(mods):
            self._make_row(i, mod)
        n = len(mods)
        self._status.configure(text=f"{n} mod{'y' if n != 1 else ''}")

    def _make_row(self, idx: int, mod: dict):
        SRC_COLORS = {
            "modrinth": "#1BD96A", "curseforge": "#F16436", "spiget": "#1E88E5"
        }
        filename = mod.get("filename", "")
        compat   = self._compat_results.get(filename)

        row = ctk.CTkFrame(self._scroll, corner_radius=6, height=70)
        row.grid(row=idx, column=0, sticky="ew", padx=4, pady=3)
        row.columnconfigure(1, weight=1)
        row.grid_propagate(False)

        src = mod.get("source", "?")
        ctk.CTkLabel(row, text=src.upper(),
                     font=ctk.CTkFont(size=9, weight="bold"),
                     text_color=SRC_COLORS.get(src, "#aaa"),
                     width=70).grid(row=0, column=0, padx=8, pady=(10, 0))

        ctk.CTkLabel(row, text=mod.get("name", filename),
                     font=ctk.CTkFont(size=12, weight="bold"),
                     anchor="w").grid(row=0, column=1, sticky="w", padx=4, pady=(10, 0))

        # compat badge
        if compat:
            ctk.CTkLabel(row, text=compat.short_label(),
                         font=ctk.CTkFont(size=10),
                         text_color=compat.color()).grid(
                row=1, column=1, sticky="w", padx=4)
        else:
            ctk.CTkLabel(row, text=filename,
                         font=ctk.CTkFont(size=10),
                         text_color="#666", anchor="w").grid(
                row=1, column=1, sticky="w", padx=4)

        btn_frame = ctk.CTkFrame(row, fg_color="transparent")
        btn_frame.grid(row=0, column=2, rowspan=2, padx=8)

        ctk.CTkButton(btn_frame, text="Zainstaluj", width=88, height=26,
                      fg_color="#FF6B35", hover_color="#e05520",
                      command=lambda m=mod: self._install_one(m)).pack(pady=(0, 3))
        ctk.CTkButton(btn_frame, text="Usuń", width=88, height=26,
                      fg_color="#3a3a3a", hover_color="#aa2222",
                      command=lambda m=mod: self._remove_one(m)).pack()

    # ── compat check ──────────────────────────────────────────────────────────

    def _run_compat_check(self):
        if not self._installation and not (self._loader and self._game_version):
            self._status.configure(
                text="⚠ Wybierz instalację w głównym oknie", text_color="#FF8C00")
            return

        self._compat_btn.configure(state="disabled", text="⏳ Sprawdzam…")
        self._status.configure(text="Sprawdzanie kompatybilności…", text_color="#888")

        inst = self._installation or {
            "loader": self._loader,
            "version": self._game_version,
        }

        def _worker():
            mods     = list_mods()
            settings = load_settings()
            results  = check_library(inst, mods, settings)

            result_map = {r.mod_name: r for r in results}
            # Mapuj też po filename (mod_name może się różnić)
            for mod, r in zip(mods, results):
                self._compat_results[mod.get("filename", "")] = r

            ok   = sum(1 for r in results if r.status == STATUS_OK)
            warn = sum(1 for r in results if r.status == STATUS_WARN)
            err  = sum(1 for r in results if r.status == STATUS_ERROR)
            unk  = sum(1 for r in results
                       if r.status not in (STATUS_OK, STATUS_WARN, STATUS_ERROR))

            summary = (f"✅ {ok}  ⚠ {warn}  ❌ {err}"
                       + (f"  ❓ {unk}" if unk else ""))

            self.after(0, lambda: self._on_compat_done(summary))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_compat_done(self, summary: str):
        self._compat_btn.configure(state="normal",
                                    text="🔍 Sprawdź kompatybilność")
        self._status.configure(text=summary, text_color="#ccc")
        self._refresh()

    # ── install / remove ──────────────────────────────────────────────────────

    def _install_one(self, mod: dict):
        ok = install_mod(mod["filename"], self._installation)
        msg = (f"✅ {mod.get('name', mod['filename'])}"
               if ok else f"❌ Błąd: {mod['filename']}")
        self._status.configure(text=msg)

    def _install_all(self):
        mods = list_mods()
        installed = sum(
            1 for m in mods if install_mod(m["filename"], self._installation))
        self._status.configure(
            text=f"✅ Zainstalowano {installed}/{len(mods)} modów")

    def _remove_one(self, mod: dict):
        remove_mod(mod["filename"])
        self._compat_results.pop(mod.get("filename", ""), None)
        self._refresh()
