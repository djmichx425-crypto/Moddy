"""
Moddy In-Game Overlay
Pokazuje się gdy gracz naciśnie hotkey (domyślnie Insert) podczas gry w Minecraft.
Wygląd inspirowany Lunar Client.
"""
from __future__ import annotations
import tkinter as tk
import customtkinter as ctk
from ..core.mod_library import load_settings, save_settings


class ModdyOverlay(ctk.CTkToplevel):
    """Fullscreen overlay z branding Moddy + szybkie opcje."""

    def __init__(self, master=None):
        super().__init__(master)

        # Fullscreen na wierzchu
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.0)

        w = self.winfo_screenwidth()
        h = self.winfo_screenheight()
        self.geometry(f"{w}x{h}+0+0")

        self._settings = load_settings()
        self._build(w, h)
        self._fade_in()

    # ── build ─────────────────────────────────────────────────────────────────

    def _build(self, w: int, h: int):
        # Tło – półprzezroczyste ciemne
        bg = tk.Frame(self, bg="#0a0a0a")
        bg.place(x=0, y=0, relwidth=1, relheight=1)
        bg.bind("<Button-1>", lambda e: self._close())  # klik poza oknem = zamknij

        # Centrum – karta
        card = ctk.CTkFrame(self, width=520, corner_radius=20,
                             fg_color="#141414",
                             border_width=1, border_color="#2a2a2a")
        card.place(relx=0.5, rely=0.5, anchor="center")
        card.pack_propagate(False)

        # Nagłówek
        hdr = ctk.CTkFrame(card, fg_color="#0d0d0d", corner_radius=0,
                            height=60)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        ctk.CTkLabel(hdr, text="⛏  moddy",
                     font=ctk.CTkFont(size=22, weight="bold"),
                     text_color="#FF6B35").pack(side="left", padx=20)
        ctk.CTkButton(hdr, text="✕ Zamknij [Insert]", width=140, height=32,
                      fg_color="#2a2a2a", hover_color="#aa2222",
                      font=ctk.CTkFont(size=11),
                      command=self._close).pack(side="right", padx=12, pady=14)

        # Zakładki
        tab = ctk.CTkTabview(card, corner_radius=8, height=320)
        tab.pack(fill="x", padx=16, pady=12)
        for t in ("⚡  Opcje", "🧥  Kosmetyki", "🎙  Głos"):
            tab.add(t)

        self._build_options(tab.tab("⚡  Opcje"))
        self._build_cosmetics(tab.tab("🧥  Kosmetyki"))
        self._build_voice(tab.tab("🎙  Głos"))

        # Przycisk "Wróć do gry"
        ctk.CTkButton(card, text="▶  Wróć do gry", height=44,
                      fg_color="#FF6B35", hover_color="#cc4400",
                      font=ctk.CTkFont(size=15, weight="bold"),
                      command=self._close).pack(fill="x", padx=16, pady=(0, 16))

    # ── zakładki ──────────────────────────────────────────────────────────────

    def _build_options(self, parent):
        toggles = [
            ("fullbright",   "☀  Fullbright",         "Maksymalna jasność bez torchy"),
            ("low_fire",     "🔥  Low Fire",            "Mniejsza nakładka ognia"),
            ("clear_water",  "💧  Clear Water",         "Przejrzysta woda pod wodą"),
            ("show_fps",     "📊  FPS Counter",         "Licznik FPS w rogu ekranu"),
            ("hit_color",    "🎯  Hit Color",           "Pomarańczowy kolor trafienia"),
            ("crosshair",    "✚  Custom Crosshair",    "Własny celownik Moddy"),
        ]
        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent", height=260)
        scroll.pack(fill="both", expand=True)

        for key, label, desc in toggles:
            row = ctk.CTkFrame(scroll, corner_radius=8, fg_color="#1e1e1e")
            row.pack(fill="x", pady=3)

            var = tk.BooleanVar(value=self._settings.get(f"overlay_{key}", False))

            ctk.CTkLabel(row, text=label,
                         font=ctk.CTkFont(size=12, weight="bold"),
                         anchor="w").pack(side="left", padx=12, pady=(8, 2))
            ctk.CTkLabel(row, text=desc,
                         font=ctk.CTkFont(size=10), text_color="#555",
                         anchor="w").pack(side="left", padx=0, pady=(8, 2))

            sw = ctk.CTkSwitch(row, text="", variable=var, width=46,
                               command=lambda k=key, v=var: self._save_toggle(k, v))
            sw.pack(side="right", padx=12, pady=8)

    def _build_cosmetics(self, parent):
        cape_key = self._settings.get("cape_url", "")

        ctk.CTkLabel(parent, text="🧥  Pelerynka",
                     font=ctk.CTkFont(size=13, weight="bold")).pack(
            anchor="w", padx=12, pady=(12, 4))
        ctk.CTkLabel(parent,
                     text="Podaj URL obrazka pelerynki (64×32 px, PNG).\n"
                          "Wymaga zainstalowanego moda Moddy Capes.",
                     font=ctk.CTkFont(size=10), text_color="#666",
                     justify="left").pack(anchor="w", padx=12)

        self._cape_entry = ctk.CTkEntry(
            parent, placeholder_text="https://example.com/cape.png",
            height=34, font=ctk.CTkFont(size=11))
        self._cape_entry.pack(fill="x", padx=12, pady=(6, 4))
        if cape_key:
            self._cape_entry.insert(0, cape_key)

        ctk.CTkButton(parent, text="Zapisz pelerynkę", height=32,
                      fg_color="#FF6B35", hover_color="#cc4400",
                      command=self._save_cape).pack(anchor="w", padx=12)

        ctk.CTkFrame(parent, height=1, fg_color="#2a2a2a").pack(
            fill="x", padx=12, pady=10)

        ctk.CTkLabel(parent, text="🎨  Skiny",
                     font=ctk.CTkFont(size=13, weight="bold")).pack(
            anchor="w", padx=12, pady=(0, 4))
        ctk.CTkLabel(parent,
                     text="Zarządzanie skinami dostępne na stronie konta Moddy.",
                     font=ctk.CTkFont(size=10), text_color="#666").pack(
            anchor="w", padx=12)

    def _build_voice(self, parent):
        s = self._settings

        ctk.CTkLabel(parent, text="🎙  Voice Chat",
                     font=ctk.CTkFont(size=13, weight="bold")).pack(
            anchor="w", padx=12, pady=(12, 4))
        ctk.CTkLabel(parent,
                     text="Wbudowany proximity voice chat.\n"
                          "Wymaga moda Simple Voice Chat zainstalowanego na serwerze.",
                     font=ctk.CTkFont(size=10), text_color="#666",
                     justify="left").pack(anchor="w", padx=12)

        form = ctk.CTkFrame(parent, fg_color="transparent")
        form.pack(fill="x", padx=12, pady=8)
        form.columnconfigure(1, weight=1)

        # PTT key
        ctk.CTkLabel(form, text="Push-to-Talk:", anchor="w",
                     font=ctk.CTkFont(size=11)).grid(row=0, column=0, sticky="w", pady=4)
        self._ptt_entry = ctk.CTkEntry(form, height=30, width=80,
                                        font=ctk.CTkFont(size=11))
        self._ptt_entry.grid(row=0, column=1, sticky="w", padx=8, pady=4)
        self._ptt_entry.insert(0, s.get("vc_ptt_key", "v"))

        # Volume
        ctk.CTkLabel(form, text="Głośność:", anchor="w",
                     font=ctk.CTkFont(size=11)).grid(row=1, column=0, sticky="w", pady=4)
        self._vol_slider = ctk.CTkSlider(form, from_=0, to=100, width=160)
        self._vol_slider.grid(row=1, column=1, sticky="w", padx=8, pady=4)
        self._vol_slider.set(s.get("vc_volume", 80))

        # Mikrofon
        ctk.CTkLabel(form, text="Mikrofon:", anchor="w",
                     font=ctk.CTkFont(size=11)).grid(row=2, column=0, sticky="w", pady=4)
        self._mic_slider = ctk.CTkSlider(form, from_=0, to=100, width=160)
        self._mic_slider.grid(row=2, column=1, sticky="w", padx=8, pady=4)
        self._mic_slider.set(s.get("vc_mic_vol", 80))

        ctk.CTkButton(parent, text="Zapisz ustawienia głosu", height=32,
                      fg_color="#2a2a2a", hover_color="#444",
                      command=self._save_voice).pack(anchor="w", padx=12, pady=4)

    # ── save helpers ──────────────────────────────────────────────────────────

    def _save_toggle(self, key: str, var: tk.BooleanVar):
        self._settings[f"overlay_{key}"] = var.get()
        save_settings(self._settings)

    def _save_cape(self):
        self._settings["cape_url"] = self._cape_entry.get().strip()
        save_settings(self._settings)

    def _save_voice(self):
        self._settings["vc_ptt_key"] = self._ptt_entry.get().strip() or "v"
        self._settings["vc_volume"]  = int(self._vol_slider.get())
        self._settings["vc_mic_vol"] = int(self._mic_slider.get())
        save_settings(self._settings)

    # ── animacja ──────────────────────────────────────────────────────────────

    def _fade_in(self, alpha: float = 0.0):
        alpha = min(alpha + 0.08, 0.92)
        self.attributes("-alpha", alpha)
        if alpha < 0.92:
            self.after(16, lambda: self._fade_in(alpha))

    def _close(self):
        def _fade(a: float = 0.92):
            a = max(a - 0.12, 0.0)
            self.attributes("-alpha", a)
            if a > 0:
                self.after(16, lambda: _fade(a))
            else:
                self.destroy()
        _fade()
