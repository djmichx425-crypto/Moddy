import tkinter as tk
import customtkinter as ctk

from ..core.mod_library import load_settings, save_settings


class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.title("Moddy – Ustawienia")
        self.geometry("480x300")
        self.resizable(False, False)
        self.grab_set()
        self._settings = load_settings()
        self._build()

    def _build(self):
        ctk.CTkLabel(self, text="Ustawienia", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(20, 16))

        form = ctk.CTkFrame(self, fg_color="transparent")
        form.pack(fill="x", padx=40)
        form.columnconfigure(1, weight=1)

        # CurseForge API key
        ctk.CTkLabel(form, text="CurseForge API Key:", anchor="w",
                     font=ctk.CTkFont(size=13)).grid(row=0, column=0, sticky="w", pady=8)
        self._cf_key = ctk.CTkEntry(form, show="*", width=240,
                                    placeholder_text="Wklej klucz API...")
        self._cf_key.grid(row=0, column=1, sticky="ew", padx=(12, 0))
        if self._settings.get("curseforge_api_key"):
            self._cf_key.insert(0, self._settings["curseforge_api_key"])

        ctk.CTkLabel(form, text="(bezpłatny klucz: console.curseforge.com)",
                     font=ctk.CTkFont(size=9), text_color="#555",
                     anchor="w").grid(row=1, column=1, sticky="w", padx=(12, 0), pady=(0, 8))

        # Theme
        ctk.CTkLabel(form, text="Motyw:", anchor="w",
                     font=ctk.CTkFont(size=13)).grid(row=2, column=0, sticky="w", pady=8)
        self._theme_var = tk.StringVar(value=self._settings.get("theme", "dark"))
        ctk.CTkOptionMenu(form, variable=self._theme_var,
                          values=["dark", "light", "system"],
                          command=lambda v: ctk.set_appearance_mode(v),
                          width=160).grid(row=2, column=1, sticky="w", padx=(12, 0))

        ctk.CTkButton(self, text="Zapisz", height=36, fg_color="#FF6B35", hover_color="#e05520",
                      command=self._save).pack(padx=40, fill="x", pady=(20, 8))

    def _save(self):
        self._settings["curseforge_api_key"] = self._cf_key.get().strip()
        self._settings["theme"] = self._theme_var.get()
        save_settings(self._settings)
        self.destroy()
