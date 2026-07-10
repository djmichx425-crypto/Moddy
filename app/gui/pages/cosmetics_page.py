"""
Strona Kosmetyki – pelerynki, skiny, ustawienia voice chat.
"""
import tkinter as tk
import customtkinter as ctk
from ...core.mod_library import load_settings, save_settings


class CosmeticsPage(ctk.CTkFrame):

    def __init__(self, parent, navigate, **kwargs):
        super().__init__(parent, corner_radius=0, fg_color="#1a1a1a", **kwargs)
        self._navigate  = navigate
        self._settings  = load_settings()
        self._build()

    def _build(self):
        top = ctk.CTkFrame(self, fg_color="#1e1e1e", corner_radius=0)
        top.pack(fill="x")
        ctk.CTkLabel(top, text="🧥  Kosmetyki",
                     font=ctk.CTkFont(size=17, weight="bold")).pack(
            side="left", padx=20, pady=13)

        tab = ctk.CTkTabview(self, corner_radius=8)
        tab.pack(fill="both", expand=True, padx=16, pady=12)
        for t in ("🧥  Pelerynki", "🎙  Voice Chat", "⚡  Overlay"):
            tab.add(t)

        self._build_capes(tab.tab("🧥  Pelerynki"))
        self._build_voice(tab.tab("🎙  Voice Chat"))
        self._build_overlay(tab.tab("⚡  Overlay"))

    # ── Pelerynki ─────────────────────────────────────────────────────────────

    def _build_capes(self, parent):
        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll.pack(fill="both", expand=True)
        scroll.columnconfigure(0, weight=1)

        # Własna pelerynka (URL)
        card = ctk.CTkFrame(scroll, corner_radius=12)
        card.grid(row=0, column=0, sticky="ew", pady=(4, 8))

        ctk.CTkLabel(card, text="🧥  Własna pelerynka",
                     font=ctk.CTkFont(size=14, weight="bold")).pack(
            anchor="w", padx=16, pady=(14, 4))
        ctk.CTkLabel(card,
                     text="Podaj URL obrazka PNG (64×32 px).\n"
                          "Pelerynka działa z modem Moddy Capes (Fabric/Forge).\n"
                          "Możesz też użyć swojej pelerynki OptiFine.",
                     font=ctk.CTkFont(size=11), text_color="#888",
                     justify="left").pack(anchor="w", padx=16)

        url_row = ctk.CTkFrame(card, fg_color="transparent")
        url_row.pack(fill="x", padx=16, pady=8)
        self._cape_entry = ctk.CTkEntry(
            url_row, placeholder_text="https://example.com/twoja-pelerynka.png",
            height=36, font=ctk.CTkFont(size=11))
        self._cape_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        ctk.CTkButton(url_row, text="Zapisz", width=80, height=36,
                      fg_color="#FF6B35", hover_color="#cc4400",
                      command=self._save_cape).pack(side="left")

        if self._settings.get("cape_url"):
            self._cape_entry.insert(0, self._settings["cape_url"])

        self._cape_status = ctk.CTkLabel(card, text="",
                                          font=ctk.CTkFont(size=10))
        self._cape_status.pack(anchor="w", padx=16, pady=(0, 14))

        # Gotowe pelerynki
        presets = ctk.CTkFrame(scroll, corner_radius=12)
        presets.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        ctk.CTkLabel(presets, text="🎨  Pelerynki Moddy",
                     font=ctk.CTkFont(size=14, weight="bold")).pack(
            anchor="w", padx=16, pady=(14, 8))

        grid = ctk.CTkFrame(presets, fg_color="transparent")
        grid.pack(fill="x", padx=16, pady=(0, 14))

        cape_presets = [
            ("🟠 Moddy Orange",   "https://moddy.app/capes/orange.png"),
            ("⬛ Moddy Dark",     "https://moddy.app/capes/dark.png"),
            ("🌊 Moddy Wave",     "https://moddy.app/capes/wave.png"),
            ("⭐ Moddy Gold",     "https://moddy.app/capes/gold.png"),
        ]
        for i, (name, url) in enumerate(cape_presets):
            btn = ctk.CTkButton(grid, text=name, height=36,
                                fg_color="#2a2a2a", hover_color="#FF6B35",
                                font=ctk.CTkFont(size=11),
                                command=lambda u=url: self._set_cape(u))
            btn.grid(row=i // 2, column=i % 2, sticky="ew",
                     padx=4, pady=3)
        grid.columnconfigure((0, 1), weight=1)

    def _set_cape(self, url: str):
        self._cape_entry.delete(0, "end")
        self._cape_entry.insert(0, url)
        self._save_cape()

    def _save_cape(self):
        url = self._cape_entry.get().strip()
        self._settings["cape_url"] = url
        save_settings(self._settings)
        self._cape_status.configure(
            text="✅ Pelerynka zapisana" if url else "Usunięto pelerynkę",
            text_color="#4CAF50" if url else "#888")

    # ── Voice Chat ────────────────────────────────────────────────────────────

    def _build_voice(self, parent):
        s = self._settings

        card = ctk.CTkFrame(parent, corner_radius=12)
        card.pack(fill="x", padx=0, pady=(4, 8))

        ctk.CTkLabel(card, text="🎙  Simple Voice Chat",
                     font=ctk.CTkFont(size=14, weight="bold")).pack(
            anchor="w", padx=16, pady=(14, 4))
        ctk.CTkLabel(card,
                     text="Wbudowany proximity voice chat.\n"
                          "Wymaga moda 'Simple Voice Chat' zainstalowanego na serwerze i u gracza.",
                     font=ctk.CTkFont(size=11), text_color="#888",
                     justify="left").pack(anchor="w", padx=16, pady=(0, 10))

        form = ctk.CTkFrame(card, fg_color="transparent")
        form.pack(fill="x", padx=16)
        form.columnconfigure(1, weight=1)

        # PTT
        ctk.CTkLabel(form, text="Push-to-Talk:", anchor="w",
                     font=ctk.CTkFont(size=12)).grid(row=0, column=0, sticky="w", pady=5)
        self._ptt = ctk.CTkEntry(form, height=32, width=60,
                                  font=ctk.CTkFont(size=12))
        self._ptt.grid(row=0, column=1, sticky="w", padx=8)
        self._ptt.insert(0, s.get("vc_ptt_key", "v"))
        ctk.CTkLabel(form, text="(jeden klawisz, np. v, caps, alt)",
                     font=ctk.CTkFont(size=10), text_color="#555").grid(
            row=0, column=2, sticky="w", padx=4)

        # Głośność wyjścia
        ctk.CTkLabel(form, text="Głośność:", anchor="w",
                     font=ctk.CTkFont(size=12)).grid(row=1, column=0, sticky="w", pady=5)
        self._vol = ctk.CTkSlider(form, from_=0, to=100, width=180)
        self._vol.grid(row=1, column=1, sticky="w", padx=8)
        self._vol.set(s.get("vc_volume", 80))
        self._vol_lbl = ctk.CTkLabel(form, text=f"{int(self._vol.get())}%",
                                      font=ctk.CTkFont(size=11), width=36)
        self._vol_lbl.grid(row=1, column=2)
        self._vol.configure(command=lambda v: self._vol_lbl.configure(text=f"{int(v)}%"))

        # Mikrofon
        ctk.CTkLabel(form, text="Mikrofon:", anchor="w",
                     font=ctk.CTkFont(size=12)).grid(row=2, column=0, sticky="w", pady=5)
        self._mic = ctk.CTkSlider(form, from_=0, to=100, width=180)
        self._mic.grid(row=2, column=1, sticky="w", padx=8)
        self._mic.set(s.get("vc_mic_vol", 80))
        self._mic_lbl = ctk.CTkLabel(form, text=f"{int(self._mic.get())}%",
                                      font=ctk.CTkFont(size=11), width=36)
        self._mic_lbl.grid(row=2, column=2)
        self._mic.configure(command=lambda v: self._mic_lbl.configure(text=f"{int(v)}%"))

        # Wycisz siebie
        self._mute_self = tk.BooleanVar(value=s.get("vc_mute_self", False))
        ctk.CTkCheckBox(card, text="Domyślnie wycisz mikrofon przy uruchomieniu",
                        variable=self._mute_self,
                        font=ctk.CTkFont(size=11)).pack(anchor="w", padx=16, pady=6)

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=(4, 14))
        ctk.CTkButton(row, text="Zapisz", height=34, width=100,
                      fg_color="#FF6B35", hover_color="#cc4400",
                      command=self._save_voice).pack(side="left")
        self._vc_status = ctk.CTkLabel(row, text="",
                                        font=ctk.CTkFont(size=10), text_color="#4CAF50")
        self._vc_status.pack(side="left", padx=10)

    def _save_voice(self):
        self._settings["vc_ptt_key"] = self._ptt.get().strip() or "v"
        self._settings["vc_volume"]  = int(self._vol.get())
        self._settings["vc_mic_vol"] = int(self._mic.get())
        self._settings["vc_mute_self"] = self._mute_self.get()
        save_settings(self._settings)
        self._vc_status.configure(text="✅ Zapisano")
        self.after(2000, lambda: self._vc_status.configure(text=""))

    # ── Overlay opcje ─────────────────────────────────────────────────────────

    def _build_overlay(self, parent):
        card = ctk.CTkFrame(parent, corner_radius=12)
        card.pack(fill="x", pady=(4, 8))

        ctk.CTkLabel(card, text="⚡  Opcje in-game",
                     font=ctk.CTkFont(size=14, weight="bold")).pack(
            anchor="w", padx=16, pady=(14, 4))
        ctk.CTkLabel(card,
                     text="Naciśnij Insert podczas gry aby otworzyć Moddy Overlay.",
                     font=ctk.CTkFont(size=11), text_color="#888").pack(
            anchor="w", padx=16, pady=(0, 10))

        toggles = [
            ("overlay_fullbright",  "☀  Fullbright",       "Maksymalna jasność bez torchy"),
            ("overlay_low_fire",    "🔥  Low Fire",          "Zmniejszona nakładka ognia na ekranie"),
            ("overlay_clear_water", "💧  Clear Water",       "Przejrzysta woda pod powierzchnią"),
            ("overlay_show_fps",    "📊  FPS Counter",       "Licznik FPS w rogu ekranu"),
            ("overlay_hit_color",   "🎯  Hit Color",         "Pomarańczowe podświetlenie trafienia"),
            ("overlay_crosshair",   "✚  Custom Crosshair",  "Własny celownik w stylu Moddy"),
        ]

        scroll = ctk.CTkScrollableFrame(card, fg_color="transparent", height=220)
        scroll.pack(fill="x", padx=8, pady=(0, 12))

        for key, label, desc in toggles:
            row = ctk.CTkFrame(scroll, corner_radius=8, fg_color="#1e1e1e")
            row.pack(fill="x", pady=2)

            var = tk.BooleanVar(value=self._settings.get(key, False))
            info = ctk.CTkFrame(row, fg_color="transparent")
            info.pack(side="left", padx=12, pady=6)
            ctk.CTkLabel(info, text=label,
                         font=ctk.CTkFont(size=12, weight="bold"),
                         anchor="w").pack(anchor="w")
            ctk.CTkLabel(info, text=desc,
                         font=ctk.CTkFont(size=10), text_color="#555",
                         anchor="w").pack(anchor="w")

            sw = ctk.CTkSwitch(row, text="", variable=var, width=46,
                               command=lambda k=key, v=var: (
                                   self._settings.update({k: v.get()}),
                                   save_settings(self._settings)
                               ))
            sw.pack(side="right", padx=12)

        # Hotkey
        hk_row = ctk.CTkFrame(card, fg_color="transparent")
        hk_row.pack(fill="x", padx=16, pady=(0, 14))
        ctk.CTkLabel(hk_row, text="Hotkey overlay:",
                     font=ctk.CTkFont(size=11)).pack(side="left")
        self._hk_entry = ctk.CTkEntry(hk_row, width=70, height=30,
                                       font=ctk.CTkFont(size=11))
        self._hk_entry.pack(side="left", padx=8)
        self._hk_entry.insert(0, self._settings.get("overlay_hotkey", "insert"))
        ctk.CTkButton(hk_row, text="Zapisz", width=70, height=30,
                      fg_color="#2a2a2a", hover_color="#444",
                      command=self._save_hotkey).pack(side="left")

    def _save_hotkey(self):
        self._settings["overlay_hotkey"] = self._hk_entry.get().strip() or "insert"
        save_settings(self._settings)

    def on_show(self, **_):
        self._settings = load_settings()
