import tkinter as tk
import customtkinter as ctk
import threading
from pathlib import Path

from ..core.mod_library import list_mods, install_mod, remove_mod, MINECRAFT_MODS


class LibraryWindow(ctk.CTkToplevel):
    def __init__(self, parent, loader: str, game_version: str, **kwargs):
        super().__init__(parent, **kwargs)
        self.loader = loader
        self.game_version = game_version
        self.title("Moddy – Biblioteka modów")
        self.geometry("640x500")
        self.resizable(True, True)
        self._build()
        self._refresh()

    def _build(self):
        top = ctk.CTkFrame(self, corner_radius=0)
        top.pack(fill="x")
        ctk.CTkLabel(top, text="📦  Biblioteka modów",
                     font=ctk.CTkFont(size=16, weight="bold")).pack(side="left", padx=14, pady=10)
        ctk.CTkLabel(top, text=f"{self.loader} {self.game_version}",
                     font=ctk.CTkFont(size=11), text_color="#888").pack(side="right", padx=14)

        self._scroll = ctk.CTkScrollableFrame(self, corner_radius=0)
        self._scroll.pack(fill="both", expand=True, padx=8, pady=4)
        self._scroll.columnconfigure(0, weight=1)

        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.pack(fill="x", padx=10, pady=8)

        self._status = ctk.CTkLabel(bottom, text="", font=ctk.CTkFont(size=11), text_color="#888")
        self._status.pack(side="left")

        ctk.CTkButton(bottom, text="✅  Zainstaluj wszystkie", height=36,
                      fg_color="#2a7a4a", hover_color="#1f5c37",
                      command=self._install_all).pack(side="right")

        ctk.CTkLabel(self, text=f"Ścieżka: {MINECRAFT_MODS}",
                     font=ctk.CTkFont(size=9), text_color="#555").pack(pady=(0, 4))

    def _refresh(self):
        for w in self._scroll.winfo_children():
            w.destroy()

        mods = list_mods()
        if not mods:
            ctk.CTkLabel(self._scroll, text="Biblioteka jest pusta. Pobierz mody w przeglądarce.",
                         font=ctk.CTkFont(size=13), text_color="#666").grid(row=0, column=0, pady=40)
            self._status.configure(text="0 modów")
            return

        for i, mod in enumerate(mods):
            self._make_row(i, mod)
        self._status.configure(text=f"{len(mods)} mod{'y' if len(mods) != 1 else ''} w bibliotece")

    def _make_row(self, idx: int, mod: dict):
        row = ctk.CTkFrame(self._scroll, corner_radius=6)
        row.grid(row=idx, column=0, sticky="ew", padx=4, pady=3)
        row.columnconfigure(1, weight=1)

        src_color = {"modrinth": "#1BD96A", "curseforge": "#F16436", "spiget": "#1E88E5"}
        src = mod.get("source", "?")
        ctk.CTkLabel(row, text=src.upper(), font=ctk.CTkFont(size=9, weight="bold"),
                     text_color=src_color.get(src, "#aaa"),
                     fg_color="transparent", width=70).grid(row=0, column=0, padx=8, pady=(8, 2))

        ctk.CTkLabel(row, text=mod.get("name", mod["filename"]),
                     font=ctk.CTkFont(size=12, weight="bold"), anchor="w").grid(row=0, column=1, sticky="w", padx=4, pady=(8, 0))
        ctk.CTkLabel(row, text=mod["filename"],
                     font=ctk.CTkFont(size=10), text_color="#777", anchor="w").grid(row=1, column=1, sticky="w", padx=4, pady=(0, 6))

        btn_frame = ctk.CTkFrame(row, fg_color="transparent")
        btn_frame.grid(row=0, column=2, rowspan=2, padx=8, pady=6)

        ctk.CTkButton(btn_frame, text="Zainstaluj", width=88, height=28,
                      fg_color="#FF6B35", hover_color="#e05520",
                      command=lambda m=mod: self._install_one(m)).pack(pady=(0, 4))
        ctk.CTkButton(btn_frame, text="Usuń", width=88, height=28,
                      fg_color="#3a3a3a", hover_color="#aa2222",
                      command=lambda m=mod: self._remove_one(m)).pack()

    def _install_one(self, mod: dict):
        ok = install_mod(mod["filename"], self.loader, self.game_version)
        if ok:
            self._status.configure(text=f"✅ Zainstalowano: {mod.get('name', mod['filename'])}")
        else:
            self._status.configure(text=f"❌ Błąd instalacji: {mod['filename']}")

    def _install_all(self):
        mods = list_mods()
        installed = 0
        for mod in mods:
            if install_mod(mod["filename"], self.loader, self.game_version):
                installed += 1
        self._status.configure(text=f"✅ Zainstalowano {installed}/{len(mods)} modów → {MINECRAFT_MODS}")

    def _remove_one(self, mod: dict):
        remove_mod(mod["filename"])
        self._refresh()
