import tkinter as tk
import customtkinter as ctk
import threading

from ..api import modrinth


COMMON_VERSIONS = [
    "1.21.6", "1.21.5", "1.21.4", "1.21.3", "1.21.1", "1.21",
    "1.20.6", "1.20.4", "1.20.2", "1.20.1", "1.20",
    "1.19.4", "1.19.2", "1.18.2", "1.17.1", "1.16.5",
]

LOADERS = ["Forge", "Fabric", "Quilt", "NeoForge", "Paper", "Spigot", "Bukkit"]


class InstallationWizard(ctk.CTkToplevel):
    def __init__(self, parent, on_create, **kwargs):
        super().__init__(parent, **kwargs)
        self.on_create = on_create
        self.title("Moddy – Nowa instalacja")
        self.geometry("460x400")
        self.resizable(False, False)
        self.grab_set()
        self._versions = COMMON_VERSIONS[:]
        self._build()
        threading.Thread(target=self._fetch_versions, daemon=True).start()

    def _build(self):
        ctk.CTkLabel(self, text="Nowa instalacja",
                     font=ctk.CTkFont(size=20, weight="bold")).pack(pady=(24, 4))
        ctk.CTkLabel(self, text="Wybierz loader i wersję Minecraft",
                     font=ctk.CTkFont(size=12), text_color="#888").pack(pady=(0, 20))

        form = ctk.CTkFrame(self, fg_color="transparent")
        form.pack(fill="x", padx=40)

        # loader
        ctk.CTkLabel(form, text="Mod loader:", anchor="w",
                     font=ctk.CTkFont(size=13)).grid(row=0, column=0, sticky="w", pady=8)
        self._loader_var = tk.StringVar(value="Forge")
        self._loader_menu = ctk.CTkOptionMenu(form, variable=self._loader_var,
                                              values=LOADERS, width=200)
        self._loader_menu.grid(row=0, column=1, sticky="ew", padx=(12, 0))

        # version
        ctk.CTkLabel(form, text="Wersja gry:", anchor="w",
                     font=ctk.CTkFont(size=13)).grid(row=1, column=0, sticky="w", pady=8)
        self._version_var = tk.StringVar(value="1.20.4")
        self._version_menu = ctk.CTkOptionMenu(form, variable=self._version_var,
                                               values=self._versions, width=200)
        self._version_menu.grid(row=1, column=1, sticky="ew", padx=(12, 0))
        form.columnconfigure(1, weight=1)

        # name
        ctk.CTkLabel(form, text="Nazwa (opcja):", anchor="w",
                     font=ctk.CTkFont(size=13)).grid(row=2, column=0, sticky="w", pady=8)
        self._name_entry = ctk.CTkEntry(form, placeholder_text="np. Survival Pack", width=200)
        self._name_entry.grid(row=2, column=1, sticky="ew", padx=(12, 0))

        self._status = ctk.CTkLabel(self, text="Ładowanie wersji...",
                                    font=ctk.CTkFont(size=10), text_color="#666")
        self._status.pack(pady=6)

        ctk.CTkButton(self, text="Utwórz instalację →", height=40,
                      font=ctk.CTkFont(size=14),
                      fg_color="#FF6B35", hover_color="#e05520",
                      command=self._confirm).pack(pady=(10, 20), padx=40, fill="x")

    def _fetch_versions(self):
        try:
            versions = modrinth.get_game_versions()
            if versions:
                self._versions = versions
                self.after(0, lambda: self._version_menu.configure(values=self._versions))
                self.after(0, lambda: self._status.configure(text=f"{len(versions)} wersji z Modrinth"))
        except Exception:
            self.after(0, lambda: self._status.configure(text="Użyto listy domyślnej"))

    def _confirm(self):
        loader = self._loader_var.get()
        version = self._version_var.get()
        name = self._name_entry.get().strip() or f"{loader} {version}"
        self.destroy()
        self.on_create(name, loader, version)
