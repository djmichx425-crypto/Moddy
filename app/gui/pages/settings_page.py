import tkinter as tk
import customtkinter as ctk
import threading

from ...core.mod_library import load_settings, save_settings
from ...core.java_manager import find_java_executables, get_java_version


class SettingsPage(ctk.CTkFrame):
    def __init__(self, parent, navigate, **kwargs):
        super().__init__(parent, corner_radius=0, fg_color="#1a1a1a", **kwargs)
        self._navigate = navigate
        self._java_list: list[str] = []
        self._build()

    def _build(self):
        # nagłówek
        top = ctk.CTkFrame(self, fg_color="#222222", corner_radius=0)
        top.pack(fill="x")
        ctk.CTkLabel(top, text="Ustawienia",
                     font=ctk.CTkFont(size=18, weight="bold")).pack(
            side="left", padx=20, pady=14)

        # scroll
        scroll = ctk.CTkScrollableFrame(self, corner_radius=0, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=12)
        scroll.columnconfigure(0, weight=1)

        # ── Sekcja: Java ─────────────────────────────────────────────────────
        java_card = self._section(scroll, "☕  Java", row=0)

        java_form = ctk.CTkFrame(java_card, fg_color="transparent")
        java_form.pack(fill="x", padx=16, pady=(0, 4))
        java_form.columnconfigure(1, weight=1)

        ctk.CTkLabel(java_form, text="Ścieżka do Java:", anchor="w",
                     font=ctk.CTkFont(size=12)).grid(row=0, column=0, sticky="w", pady=6)
        self._java_var = tk.StringVar(value="Auto")
        self._java_menu = ctk.CTkOptionMenu(
            java_form, variable=self._java_var, values=["Auto"], width=320)
        self._java_menu.grid(row=0, column=1, sticky="ew", padx=(10, 0))

        self._java_ver_lbl = ctk.CTkLabel(
            java_form, text="", font=ctk.CTkFont(size=10),
            text_color="#888", anchor="w")
        self._java_ver_lbl.grid(row=1, column=1, sticky="w", padx=(10, 0))

        ctk.CTkButton(java_form, text="Wykryj Javę", width=110, height=28,
                      fg_color="#3a3a3a", hover_color="#555",
                      command=self._detect_java).grid(
            row=0, column=2, padx=(8, 0))

        # ── Sekcja: Pamięć ───────────────────────────────────────────────────
        mem_card = self._section(scroll, "🧠  Pamięć RAM (domyślna)", row=1)
        mem_form = ctk.CTkFrame(mem_card, fg_color="transparent")
        mem_form.pack(fill="x", padx=16, pady=(0, 14))
        mem_form.columnconfigure(1, weight=1)

        ctk.CTkLabel(mem_form, text="Domyślne RAM (MB):", anchor="w",
                     font=ctk.CTkFont(size=12)).grid(row=0, column=0, sticky="w", pady=6)
        self._memory_var = tk.StringVar(value="2048")
        ctk.CTkOptionMenu(
            mem_form, variable=self._memory_var,
            values=["1024", "2048", "3072", "4096", "6144", "8192"],
            width=120).grid(row=0, column=1, sticky="w", padx=(10, 0))

        ctk.CTkLabel(mem_form, text="Minimalne: 512 MB  •  Zalecane: 2048–4096 MB",
                     font=ctk.CTkFont(size=10), text_color="#555",
                     anchor="w").grid(row=1, column=0, columnspan=3, sticky="w", pady=(0, 4))

        # ── Sekcja: Modrinth / CurseForge ────────────────────────────────────
        api_card = self._section(scroll, "🔑  API Keys", row=2)
        api_form = ctk.CTkFrame(api_card, fg_color="transparent")
        api_form.pack(fill="x", padx=16, pady=(0, 14))
        api_form.columnconfigure(1, weight=1)

        ctk.CTkLabel(api_form, text="CurseForge API Key:", anchor="w",
                     font=ctk.CTkFont(size=12)).grid(row=0, column=0, sticky="w", pady=6)
        self._cf_key = ctk.CTkEntry(api_form, show="*", width=280,
                                    placeholder_text="Wklej klucz API…")
        self._cf_key.grid(row=0, column=1, sticky="ew", padx=(10, 0))

        ctk.CTkLabel(api_form, text="Pobierz na: console.curseforge.com",
                     font=ctk.CTkFont(size=9), text_color="#555",
                     anchor="w").grid(row=1, column=1, sticky="w", padx=(10, 0))

        # ── Sekcja: Wygląd ───────────────────────────────────────────────────
        ui_card = self._section(scroll, "🎨  Wygląd", row=3)
        ui_form = ctk.CTkFrame(ui_card, fg_color="transparent")
        ui_form.pack(fill="x", padx=16, pady=(0, 14))
        ui_form.columnconfigure(1, weight=1)

        ctk.CTkLabel(ui_form, text="Motyw:", anchor="w",
                     font=ctk.CTkFont(size=12)).grid(row=0, column=0, sticky="w", pady=6)
        self._theme_var = tk.StringVar(value="dark")
        ctk.CTkOptionMenu(ui_form, variable=self._theme_var,
                          values=["dark", "light", "system"],
                          command=lambda v: ctk.set_appearance_mode(v),
                          width=130).grid(row=0, column=1, sticky="w", padx=(10, 0))

        # ── Zapisz ───────────────────────────────────────────────────────────
        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.pack(fill="x", padx=20, pady=(0, 16))

        self._saved_lbl = ctk.CTkLabel(bottom, text="",
                                        font=ctk.CTkFont(size=12), text_color="#4CAF50")
        self._saved_lbl.pack(side="left", padx=4)

        ctk.CTkButton(bottom, text="Zapisz ustawienia", height=36, width=180,
                      fg_color="#FF6B35", hover_color="#e05520",
                      command=self._save).pack(side="right")

    def _section(self, parent, title: str, row: int) -> ctk.CTkFrame:
        card = ctk.CTkFrame(parent, corner_radius=12)
        card.grid(row=row, column=0, sticky="ew", pady=6)
        ctk.CTkLabel(card, text=title,
                     font=ctk.CTkFont(size=13, weight="bold")).pack(
            anchor="w", padx=16, pady=(12, 6))
        return card

    # ── on_show ───────────────────────────────────────────────────────────────

    def on_show(self, **_):
        s = load_settings()
        self._cf_key.delete(0, "end")
        if s.get("curseforge_api_key"):
            self._cf_key.insert(0, s["curseforge_api_key"])
        self._theme_var.set(s.get("theme", "dark"))
        self._memory_var.set(str(s.get("default_memory_mb", 2048)))
        java_path = s.get("java_path", "Auto")
        self._java_var.set(java_path or "Auto")
        self._saved_lbl.configure(text="")

        # Wykryj Javę w tle
        if not self._java_list:
            threading.Thread(target=self._detect_java, daemon=True).start()

    # ── java detect ───────────────────────────────────────────────────────────

    def _detect_java(self):
        self.after(0, lambda: self._java_ver_lbl.configure(text="Szukam Javy…"))
        javas = find_java_executables()
        self._java_list = javas
        options = ["Auto"] + javas
        self.after(0, lambda: self._java_menu.configure(values=options))

        if javas:
            # Pokaż wersję aktualnie wybranej
            cur = self._java_var.get()
            if cur == "Auto":
                ver = get_java_version(javas[0])
            else:
                ver = get_java_version(cur) if cur in javas else ""
            self.after(0, lambda v=ver: self._java_ver_lbl.configure(
                text=f"Znaleziono {len(javas)} instalacji  •  {v}"))
        else:
            self.after(0, lambda: self._java_ver_lbl.configure(
                text="⚠ Nie znaleziono Javy! Zainstaluj Java 17+",
                text_color="#FF8C00"))

    # ── save ──────────────────────────────────────────────────────────────────

    def _save(self):
        s = load_settings()
        s["curseforge_api_key"] = self._cf_key.get().strip()
        s["theme"] = self._theme_var.get()
        s["default_memory_mb"] = int(self._memory_var.get())
        java = self._java_var.get()
        s["java_path"] = "" if java == "Auto" else java
        save_settings(s)
        self._saved_lbl.configure(text="✓ Zapisano!")
        self.after(2500, lambda: self._saved_lbl.configure(text=""))
