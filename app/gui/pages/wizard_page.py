"""
Kreator nowej instalacji Minecraft.
Krok 1: Wybór loadera, wersji, nazwy, pamięci.
Krok 2: Pobieranie / instalacja (przejście do PlayPage).
"""
import tkinter as tk
import customtkinter as ctk
import threading

from ...core import minecraft_launcher as launcher


LOADERS = ["Vanilla", "Fabric", "Forge", "Quilt", "NeoForge"]
LOADER_DESCRIPTIONS = {
    "Vanilla":  "Czysta wersja Minecraft bez modów.",
    "Fabric":   "Lekki loader — najlepszy dla nowych wersji.",
    "Forge":    "Klasyczny loader, największa ilość modów.",
    "Quilt":    "Fork Fabric z dodatkowymi funkcjami.",
    "NeoForge": "Nowoczesny fork Forge (od 1.20.2).",
}


class WizardPage(ctk.CTkFrame):
    def __init__(self, parent, navigate, on_create, **kwargs):
        super().__init__(parent, corner_radius=0, fg_color="#1a1a1a", **kwargs)
        self._navigate = navigate
        self._on_create = on_create
        self._loader_versions: dict[str, list[str]] = {}
        # Załaduj listę domyślną od razu (zanim API odpowie)
        self._all_versions = launcher.get_version_list(include_snapshots=True)
        self._build()
        # Odśwież z API w tle
        threading.Thread(target=self._fetch_data, daemon=True).start()

    # ── build ─────────────────────────────────────────────────────────────────

    def _build(self):
        card = ctk.CTkFrame(self, corner_radius=16, width=500)
        card.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(card, text="Nowa instalacja",
                     font=ctk.CTkFont(size=22, weight="bold")).pack(pady=(28, 4))
        ctk.CTkLabel(card, text="Skonfiguruj swoją instalację Minecraft",
                     font=ctk.CTkFont(size=12), text_color="#888").pack(pady=(0, 20))

        form = ctk.CTkFrame(card, fg_color="transparent")
        form.pack(fill="x", padx=40)
        form.columnconfigure(1, weight=1)

        row = 0

        # Mod loader
        ctk.CTkLabel(form, text="Mod loader:", anchor="w",
                     font=ctk.CTkFont(size=13)).grid(row=row, column=0, sticky="w", pady=8)
        self._loader_var = tk.StringVar(value="Fabric")
        self._loader_menu = ctk.CTkOptionMenu(
            form, variable=self._loader_var, values=LOADERS,
            width=200, command=self._on_loader_change)
        self._loader_menu.grid(row=row, column=1, sticky="ew", padx=(12, 0))
        row += 1

        # Opis loadera
        self._loader_desc = ctk.CTkLabel(
            form, text=LOADER_DESCRIPTIONS["Fabric"],
            font=ctk.CTkFont(size=10), text_color="#666",
            anchor="w", wraplength=220)
        self._loader_desc.grid(row=row, column=1, sticky="w", padx=(12, 0), pady=(0, 4))
        row += 1

        # Wersja Minecraft
        ctk.CTkLabel(form, text="Wersja Minecraft:", anchor="w",
                     font=ctk.CTkFont(size=13)).grid(row=row, column=0, sticky="w", pady=8)
        self._version_var = tk.StringVar(value="1.21.1")
        self._version_menu = ctk.CTkOptionMenu(
            form, variable=self._version_var, values=["1.21.1"],
            width=200, command=self._on_version_change)
        self._version_menu.grid(row=row, column=1, sticky="ew", padx=(12, 0))
        row += 1

        # Wersja loadera (fabric/forge/etc)
        ctk.CTkLabel(form, text="Wersja loadera:", anchor="w",
                     font=ctk.CTkFont(size=13)).grid(row=row, column=0, sticky="w", pady=8)
        self._loader_ver_var = tk.StringVar(value="Najnowsza")
        self._loader_ver_menu = ctk.CTkOptionMenu(
            form, variable=self._loader_ver_var, values=["Najnowsza"],
            width=200)
        self._loader_ver_menu.grid(row=row, column=1, sticky="ew", padx=(12, 0))
        row += 1

        # Nazwa
        ctk.CTkLabel(form, text="Nazwa:", anchor="w",
                     font=ctk.CTkFont(size=13)).grid(row=row, column=0, sticky="w", pady=8)
        self._name_entry = ctk.CTkEntry(
            form, placeholder_text="np. Survival Pack", width=200)
        self._name_entry.grid(row=row, column=1, sticky="ew", padx=(12, 0))
        row += 1

        # Pamięć RAM
        ctk.CTkLabel(form, text="RAM (MB):", anchor="w",
                     font=ctk.CTkFont(size=13)).grid(row=row, column=0, sticky="w", pady=8)
        self._memory_var = tk.StringVar(value="2048")
        ctk.CTkOptionMenu(
            form, variable=self._memory_var,
            values=["1024", "2048", "3072", "4096", "6144", "8192"],
            width=200).grid(row=row, column=1, sticky="ew", padx=(12, 0))
        row += 1

        # Snapshoty
        self._snap_var = tk.BooleanVar(value=False)
        snap_row = ctk.CTkFrame(form, fg_color="transparent")
        snap_row.grid(row=row, column=0, columnspan=2, sticky="w", pady=(4, 0))
        ctk.CTkCheckBox(snap_row, text="Pokaż snapshoty",
                        variable=self._snap_var,
                        command=self._refresh_versions,
                        font=ctk.CTkFont(size=11),
                        text_color="#888").pack(side="left")
        row += 1

        # Status ładowania
        self._status = ctk.CTkLabel(card, text="⏳ Ładowanie listy wersji…",
                                     font=ctk.CTkFont(size=10), text_color="#555")
        self._status.pack(pady=8)

        # Przyciski
        btns = ctk.CTkFrame(card, fg_color="transparent")
        btns.pack(padx=40, fill="x", pady=(0, 28))
        ctk.CTkButton(btns, text="Anuluj", height=36, width=100,
                      fg_color="#3a3a3a", hover_color="#555",
                      command=lambda: self._navigate("home")).pack(side="left")
        self._create_btn = ctk.CTkButton(
            btns, text="Utwórz →", height=36,
            fg_color="#FF6B35", hover_color="#e05520",
            command=self._confirm)
        self._create_btn.pack(side="right")

    # ── data fetching ─────────────────────────────────────────────────────────

    def _fetch_data(self):
        try:
            versions = launcher.get_version_list(include_snapshots=True)
            self._all_versions = versions
            self.after(0, self._refresh_versions)
            self.after(0, lambda: self._status.configure(
                text=f"✓ {len(versions)} wersji załadowanych"))
        except Exception as e:
            msg = str(e)
            self.after(0, lambda m=msg: self._status.configure(
                text="⚠ Brak internetu – lista domyślna"))
            self._all_versions = launcher.get_version_list(include_snapshots=True)
            self.after(0, self._refresh_versions)   # ← brakowało tego

        # Fabric loader versions
        try:
            fab_loaders = launcher.get_fabric_loader_versions()
            self._loader_versions["fabric"] = ["Najnowsza"] + fab_loaders
        except Exception:
            self._loader_versions["fabric"] = ["Najnowsza"]

        try:
            quilt_loaders = launcher.get_quilt_loader_versions()
            self._loader_versions["quilt"] = ["Najnowsza"] + quilt_loaders
        except Exception:
            self._loader_versions["quilt"] = ["Najnowsza"]

    def _refresh_versions(self):
        try:
            all_v = getattr(self, "_all_versions", [])
        except Exception:
            all_v = []

        show_snaps = self._snap_var.get()
        if show_snaps:
            ids = [v["id"] for v in all_v]
        else:
            ids = [v["id"] for v in all_v if v.get("type") == "release"]

        if not ids:
            ids = ["1.21.1", "1.21", "1.20.4", "1.20.1", "1.19.4", "1.18.2",
                   "1.16.5", "1.12.2", "1.8.9"]

        self._versions = ids
        self._version_menu.configure(values=ids)
        if self._version_var.get() not in ids:
            self._version_var.set(ids[0])

    def _on_loader_change(self, value: str):
        self._loader_desc.configure(text=LOADER_DESCRIPTIONS.get(value, ""))
        self._update_loader_versions(value)

    def _on_version_change(self, mc_version: str):
        loader = self._loader_var.get()
        if loader == "Forge":
            threading.Thread(target=self._fetch_forge_ver,
                             args=(mc_version,), daemon=True).start()

    def _fetch_forge_ver(self, mc_version: str):
        forge_ver = launcher.get_forge_version(mc_version)
        if forge_ver:
            self._loader_versions["forge"] = ["Najnowsza", forge_ver]
        else:
            self._loader_versions["forge"] = ["Brak Forge dla tej wersji"]
        self.after(0, lambda: self._update_loader_versions("Forge"))

    def _update_loader_versions(self, loader: str):
        loader_key = loader.lower().replace(" ", "")
        versions = self._loader_versions.get(loader_key, ["Najnowsza"])
        self._loader_ver_menu.configure(values=versions)
        self._loader_ver_var.set(versions[0])

        # Vanilla i NeoForge nie mają osobnych wersji loadera
        if loader in ("Vanilla",):
            self._loader_ver_menu.configure(state="disabled")
        else:
            self._loader_ver_menu.configure(state="normal")

    # ── on_show ───────────────────────────────────────────────────────────────

    def on_show(self, **_):
        self._name_entry.delete(0, "end")
        self._status.configure(text="")

    # ── confirm ───────────────────────────────────────────────────────────────

    def _confirm(self):
        loader = self._loader_var.get()
        version = self._version_var.get()
        name = self._name_entry.get().strip() or f"{loader} {version}"
        memory = int(self._memory_var.get())
        loader_ver = self._loader_ver_var.get()
        if loader_ver in ("Najnowsza", "Brak Forge dla tej wersji"):
            loader_ver = None

        self._on_create(name, loader, version, memory, loader_ver)
