"""
Strona Paczki Modów.

Zakładki:
  1. Moje paczki  – lista zapisanych paczek, przycisk Zainstaluj / Usuń / Eksportuj
  2. Utwórz       – kreator nowej paczki z biblioteki
  3. Importuj     – otwieranie pliku .modpack z dysku
"""
import tkinter as tk
import tkinter.filedialog as fd
import customtkinter as ctk
import threading

from ...core.modpack_manager import (
    list_modpacks, save_modpack, delete_modpack, export_modpack,
    load_modpack_file, create_modpack, get_library_mods_for,
)
from ...core.mod_library import load_installations, load_settings


class ModpacksPage(ctk.CTkFrame):

    def __init__(self, parent, navigate,
                 on_install_modpack=None, **kwargs):
        super().__init__(parent, corner_radius=0, fg_color="#1a1a1a", **kwargs)
        self._navigate = navigate
        self._on_install_modpack = on_install_modpack   # callback → main_window
        self._build()

    # ── build ─────────────────────────────────────────────────────────────────

    def _build(self):
        # nagłówek
        top = ctk.CTkFrame(self, fg_color="#1e1e1e", corner_radius=0)
        top.pack(fill="x")
        ctk.CTkLabel(top, text="Paczki modów",
                     font=ctk.CTkFont(size=17, weight="bold")).pack(
            side="left", padx=20, pady=13)

        # zakładki
        self._tab = ctk.CTkTabview(self, corner_radius=8)
        self._tab.pack(fill="both", expand=True, padx=16, pady=12)

        self._tab.add("📦  Moje paczki")
        self._tab.add("✏  Utwórz")
        self._tab.add("📂  Importuj")

        self._build_my_packs(self._tab.tab("📦  Moje paczki"))
        self._build_creator(self._tab.tab("✏  Utwórz"))
        self._build_import(self._tab.tab("📂  Importuj"))

    # ══════════════════════════════════════════════════════════════════════════
    #  ZAKŁADKA 1 – Moje paczki
    # ══════════════════════════════════════════════════════════════════════════

    def _build_my_packs(self, parent):
        self._packs_scroll = ctk.CTkScrollableFrame(
            parent, corner_radius=0, fg_color="transparent")
        self._packs_scroll.pack(fill="both", expand=True)
        self._packs_scroll.columnconfigure(0, weight=1)

    def _refresh_my_packs(self):
        for w in self._packs_scroll.winfo_children():
            w.destroy()

        # Zawsze widoczny przykładowy modpack
        self._make_starter_card(0)

        packs = list_modpacks()
        for i, pack in enumerate(packs, start=1):
            self._make_pack_card(i, pack)

    def _make_starter_card(self, idx: int):
        card = ctk.CTkFrame(self._packs_scroll, corner_radius=12,
                             border_width=1, border_color="#FF6B35")
        card.grid(row=idx, column=0, sticky="ew", pady=(0, 8))
        card.columnconfigure(1, weight=1)

        # Badge
        badge = ctk.CTkFrame(card, fg_color="#FF6B35", corner_radius=6, width=6)
        badge.grid(row=0, column=0, rowspan=2, sticky="ns", padx=(12, 10), pady=12)

        # Info
        ctk.CTkLabel(card,
                     text="⭐  Moddy Starter Pack",
                     font=ctk.CTkFont(size=13, weight="bold")).grid(
            row=0, column=1, sticky="w", pady=(12, 2))
        ctk.CTkLabel(card,
                     text="Fabric 1.21.1  •  3 mody  •  Fullbright • Low Fire • Clear Water",
                     font=ctk.CTkFont(size=10), text_color="#888").grid(
            row=1, column=1, sticky="w", pady=(0, 12))

        # Przycisk
        ctk.CTkButton(card, text="⬇ Zainstaluj", width=110, height=30,
                      fg_color="#FF6B35", hover_color="#cc4400",
                      font=ctk.CTkFont(size=11),
                      command=self._install_starter).grid(
            row=0, column=2, rowspan=2, padx=12, pady=12)

    def _make_pack_card(self, idx: int, pack: dict):
        LOADER_COLORS = {
            "vanilla": "#4CAF50", "fabric": "#7EB5D6",
            "forge": "#A0522D", "quilt": "#9370DB", "neoforge": "#FF8C00",
        }
        loader = pack.get("loader", "vanilla")
        color  = LOADER_COLORS.get(loader.lower(), "#555")
        n_mods = len(pack.get("mods", []))

        card = ctk.CTkFrame(self._packs_scroll, corner_radius=10, height=100)
        card.grid(row=idx, column=0, sticky="ew", padx=4, pady=5)
        card.columnconfigure(1, weight=1)
        card.grid_propagate(False)

        # loader badge
        left = ctk.CTkFrame(card, fg_color="transparent", width=90)
        left.grid(row=0, column=0, rowspan=3, padx=(12, 6), pady=10, sticky="ns")
        left.pack_propagate(False)
        ctk.CTkLabel(left, text=loader.upper(),
                     font=ctk.CTkFont(size=10, weight="bold"),
                     fg_color=color, corner_radius=5,
                     text_color="white", width=82, height=24).pack()
        mc_ver = pack.get("minecraft_version", "")
        ctk.CTkLabel(left, text=mc_ver,
                     font=ctk.CTkFont(size=9), text_color="#888").pack(pady=(2, 0))
        ctk.CTkLabel(left, text=f"{n_mods} modów",
                     font=ctk.CTkFont(size=9), text_color="#666").pack()

        # info
        ctk.CTkLabel(card, text=pack.get("name", "Paczka"),
                     font=ctk.CTkFont(size=14, weight="bold"),
                     anchor="w").grid(row=0, column=1, sticky="w", pady=(12, 0))

        desc = pack.get("description", "")[:80] or "Brak opisu"
        ctk.CTkLabel(card, text=desc,
                     font=ctk.CTkFont(size=11), text_color="#888",
                     anchor="w").grid(row=1, column=1, sticky="w")

        author = pack.get("author", "")
        ver    = pack.get("version", "")
        ctk.CTkLabel(card, text=f"Autor: {author}  •  v{ver}",
                     font=ctk.CTkFont(size=10), text_color="#555",
                     anchor="w").grid(row=2, column=1, sticky="w", pady=(0, 10))

        # przyciski
        btns = ctk.CTkFrame(card, fg_color="transparent")
        btns.grid(row=0, column=2, rowspan=3, padx=10, sticky="ns")

        ctk.CTkButton(btns, text="▶  Zainstaluj", width=110, height=34,
                      fg_color="#4CAF50", hover_color="#388E3C",
                      font=ctk.CTkFont(size=12, weight="bold"),
                      command=lambda p=pack: self._install_pack(p)).pack(pady=(12, 4))

        row2 = ctk.CTkFrame(btns, fg_color="transparent")
        row2.pack()
        ctk.CTkButton(row2, text="Eksportuj", width=52, height=26,
                      fg_color="#3a3a3a", hover_color="#555",
                      command=lambda p=pack: self._export_pack(p)).pack(side="left", padx=(0, 3))
        ctk.CTkButton(row2, text="✕", width=28, height=26,
                      fg_color="#3a3a3a", hover_color="#aa2222",
                      command=lambda p=pack: self._delete_pack(p)).pack(side="left")

    def _install_pack(self, pack: dict):
        if self._on_install_modpack:
            self._on_install_modpack(pack)

    def _export_pack(self, pack: dict):
        path = fd.asksaveasfilename(
            defaultextension=".modpack",
            filetypes=[("Paczka Moddy", "*.modpack"), ("JSON", "*.json")],
            initialfile=pack.get("name", "paczka") + ".modpack",
            title="Eksportuj paczkę")
        if path:
            export_modpack(pack, path)
            self._show_toast(f"Wyeksportowano: {path}")

    def _delete_pack(self, pack: dict):
        delete_modpack(pack.get("_path", ""))
        self._refresh_my_packs()

    def _show_toast(self, msg: str):
        # Krótki komunikat w oknie
        w = ctk.CTkToplevel(self)
        w.title("")
        w.geometry("380x60")
        w.resizable(False, False)
        ctk.CTkLabel(w, text=msg, font=ctk.CTkFont(size=12)).pack(expand=True)
        w.after(2500, w.destroy)

    # ══════════════════════════════════════════════════════════════════════════
    #  ZAKŁADKA 2 – Utwórz
    # ══════════════════════════════════════════════════════════════════════════

    def _build_creator(self, parent):
        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll.pack(fill="both", expand=True)
        scroll.columnconfigure(0, weight=1)

        # Karta formularza
        card = ctk.CTkFrame(scroll, corner_radius=12)
        card.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        card.columnconfigure(1, weight=1)

        ctk.CTkLabel(card, text="Nowa paczka modów",
                     font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=0, column=0, columnspan=2, padx=16, pady=(16, 12), sticky="w")

        fields = [
            ("Nazwa paczki:", "Moja paczka"),
            ("Wersja:",       "1.0.0"),
            ("Autor:",        ""),
            ("Opis:",         ""),
        ]
        self._create_entries: dict[str, ctk.CTkEntry] = {}
        for i, (label, placeholder) in enumerate(fields, start=1):
            ctk.CTkLabel(card, text=label, anchor="w",
                         font=ctk.CTkFont(size=12)).grid(
                row=i, column=0, sticky="w", padx=16, pady=6)
            e = ctk.CTkEntry(card, placeholder_text=placeholder, height=32)
            e.grid(row=i, column=1, sticky="ew", padx=(8, 16), pady=6)
            self._create_entries[label] = e

        # Wybór instalacji
        ctk.CTkLabel(card, text="Instalacja:", anchor="w",
                     font=ctk.CTkFont(size=12)).grid(
            row=5, column=0, sticky="w", padx=16, pady=6)
        self._create_inst_var = tk.StringVar()
        self._create_inst_menu = ctk.CTkOptionMenu(
            card, variable=self._create_inst_var, values=["Brak instalacji"],
            command=self._on_creator_inst_change)
        self._create_inst_menu.grid(row=5, column=1, sticky="ew", padx=(8, 16), pady=6)

        # Lista modów (checkboxy)
        ctk.CTkLabel(card, text="Mody:",
                     font=ctk.CTkFont(size=12), anchor="w").grid(
            row=6, column=0, sticky="nw", padx=16, pady=(10, 0))

        self._mods_frame = ctk.CTkScrollableFrame(card, height=160)
        self._mods_frame.grid(row=6, column=1, sticky="ew",
                              padx=(8, 16), pady=(6, 10))
        self._mod_vars: dict[str, tk.BooleanVar] = {}

        self._create_status = ctk.CTkLabel(card, text="",
                                            font=ctk.CTkFont(size=11),
                                            text_color="#4CAF50")
        self._create_status.grid(row=7, column=0, columnspan=2, pady=4)

        # Przyciski
        btn_row = ctk.CTkFrame(card, fg_color="transparent")
        btn_row.grid(row=8, column=0, columnspan=2,
                     padx=16, pady=(0, 16), sticky="e")
        ctk.CTkButton(btn_row, text="✓  Utwórz paczkę", height=36, width=160,
                      fg_color="#FF6B35", hover_color="#e05520",
                      command=self._do_create).pack()

    def _on_creator_inst_change(self, name: str):
        """Załaduj mody biblioteki pasujące do wybranej instalacji."""
        for w in self._mods_frame.winfo_children():
            w.destroy()
        self._mod_vars.clear()

        inst = self._get_installation_by_name(name)
        if not inst:
            return

        loader  = inst.get("loader", "")
        mc_ver  = inst.get("version") or inst.get("game_version", "")
        mods    = get_library_mods_for(loader, mc_ver)

        if not mods:
            ctk.CTkLabel(self._mods_frame,
                         text=f"Brak modów w bibliotece dla {loader} {mc_ver}.\n"
                              "Pobierz mody w Przeglądarce.",
                         font=ctk.CTkFont(size=11), text_color="#666",
                         justify="left").pack(anchor="w", padx=4, pady=8)
            return

        # Zaznacz wszystkie domyślnie
        for mod in mods:
            fname = mod["filename"]
            var = tk.BooleanVar(value=True)
            self._mod_vars[fname] = var
            row = ctk.CTkFrame(self._mods_frame, fg_color="transparent")
            row.pack(fill="x", pady=1)
            ctk.CTkCheckBox(row, text=mod.get("name", fname),
                            variable=var,
                            font=ctk.CTkFont(size=11)).pack(side="left", padx=4)
            src = mod.get("source", "")
            SRC = {"modrinth": "#1BD96A", "curseforge": "#F16436", "spiget": "#1E88E5"}
            ctk.CTkLabel(row, text=src, font=ctk.CTkFont(size=9),
                         text_color=SRC.get(src, "#888")).pack(side="left")

    def _do_create(self):
        inst_name = self._create_inst_var.get()
        inst = self._get_installation_by_name(inst_name)
        if not inst:
            self._create_status.configure(text="⚠ Wybierz instalację", text_color="#FF8C00")
            return

        name  = self._create_entries["Nazwa paczki:"].get().strip() or "Moja paczka"
        ver   = self._create_entries["Wersja:"].get().strip() or "1.0.0"
        author = self._create_entries["Autor:"].get().strip()
        desc  = self._create_entries["Opis:"].get().strip()

        loader  = inst.get("loader", "")
        mc_ver  = inst.get("version") or inst.get("game_version", "")
        all_mods = get_library_mods_for(loader, mc_ver)

        selected = [m for m in all_mods
                    if self._mod_vars.get(m["filename"], tk.BooleanVar(value=True)).get()]

        if not selected:
            self._create_status.configure(
                text="⚠ Zaznacz przynajmniej jeden mod", text_color="#FF8C00")
            return

        # Upewnij się, że każdy mod ma download_url
        mods_clean = [
            {
                "name":         m.get("name", m["filename"]),
                "source":       m.get("source", ""),
                "mod_id":       m.get("mod_id", ""),
                "filename":     m["filename"],
                "download_url": m.get("download_url", ""),
            }
            for m in selected
        ]

        pack = create_modpack(name, desc, author, ver, inst, mods_clean)
        self._create_status.configure(
            text=f"✓ Utworzono: '{name}' ({len(mods_clean)} modów)",
            text_color="#4CAF50")
        self._refresh_my_packs()
        self._tab.set("📦  Moje paczki")

    # ══════════════════════════════════════════════════════════════════════════
    #  ZAKŁADKA 3 – Importuj
    # ══════════════════════════════════════════════════════════════════════════

    def _build_import(self, parent):
        box = ctk.CTkFrame(parent, corner_radius=12)
        box.place(relx=0.5, rely=0.4, anchor="center")

        ctk.CTkLabel(box, text="📂  Importuj paczkę",
                     font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(28, 8))
        ctk.CTkLabel(box,
                     text="Otwórz plik .modpack pobrany od znajomego\n"
                          "lub ze społeczności i zainstaluj go jednym kliknięciem.",
                     font=ctk.CTkFont(size=12), text_color="#888",
                     justify="center").pack(padx=30)

        ctk.CTkButton(box, text="📂  Wybierz plik .modpack", height=42, width=240,
                      fg_color="#FF6B35", hover_color="#e05520",
                      font=ctk.CTkFont(size=14),
                      command=self._open_file).pack(pady=20)

        self._import_info = ctk.CTkFrame(box, fg_color="#222", corner_radius=8)
        self._import_info.pack(fill="x", padx=20, pady=(0, 10))

        self._import_lbl = ctk.CTkLabel(
            self._import_info, text="",
            font=ctk.CTkFont(size=11), text_color="#aaa",
            justify="left")
        self._import_lbl.pack(padx=12, pady=8)

        self._import_btn = ctk.CTkButton(
            box, text="▶  Zainstaluj", height=38, width=200,
            fg_color="#4CAF50", hover_color="#388E3C",
            font=ctk.CTkFont(size=13, weight="bold"),
            state="disabled",
            command=self._install_imported)
        self._import_btn.pack(pady=(0, 24))

        self._imported_pack: dict | None = None

    def _open_file(self):
        path = fd.askopenfilename(
            filetypes=[("Paczka Moddy", "*.modpack"), ("JSON", "*.json"), ("Wszystkie", "*.*")],
            title="Wybierz plik .modpack")
        if not path:
            return
        try:
            pack = load_modpack_file(path)
            # Zapisz lokalnie
            save_modpack(pack)
            self._imported_pack = pack
            self._refresh_my_packs()

            n_mods  = len(pack.get("mods", []))
            loader  = pack.get("loader", "?")
            mc_ver  = pack.get("minecraft_version", "?")
            name    = pack.get("name", "?")
            author  = pack.get("author", "?")
            self._import_lbl.configure(
                text=f"Nazwa:   {name}\n"
                     f"Autor:   {author}\n"
                     f"Wersja:  Minecraft {mc_ver}  •  {loader.capitalize()}\n"
                     f"Mody:    {n_mods} modów")
            self._import_btn.configure(state="normal")
        except Exception as e:
            self._import_lbl.configure(
                text=f"❌ Błąd: {e}", text_color="#FF4444")
            self._import_btn.configure(state="disabled")

    def _install_imported(self):
        if self._imported_pack and self._on_install_modpack:
            self._on_install_modpack(self._imported_pack)

    # ── Moddy Starter Pack ────────────────────────────────────────────────────

    # Modrinth project IDs dla Fabric 1.21.1
    _STARTER_MODS = [
        {"name": "Fabric API",   "id": "P7dR8mSH", "file_hint": "fabric-api"},
        {"name": "Fullbright",   "id": "YSNjU7Q9", "file_hint": "fullbright"},
        {"name": "Lowfire",      "id": "8shC1gFX", "file_hint": "lowfire"},
    ]
    _STARTER_PACKS = [
        # Resource pack – Clear Water (pobierz z CurseForge/GitHub bo Modrinth go nie ma)
        {"name": "Clear Water & Fire", "url":
         "https://github.com/RealClearWater/ClearWaterFire/releases/latest/download/ClearWaterFire.zip"},
    ]

    def _install_starter(self):
        import os, requests
        from ...core.mod_library import load_installations
        from pathlib import Path

        insts = load_installations()
        if not insts:
            self._starter_status("⚠ Najpierw utwórz instalację Fabric 1.21.1")
            return

        # Użyj pierwszej instalacji Fabric, albo pierwszej dostępnej
        inst = next(
            (i for i in insts if "fabric" in i.get("loader", "").lower()), insts[0])
        mods_dir = Path(os.environ.get("APPDATA", "~")) / "moddy" / "instances" / \
                   inst.get("name", "default").replace(" ", "_") / "mods"
        mods_dir.mkdir(parents=True, exist_ok=True)

        self._starter_status("⏳ Pobieranie Moddy Starter Pack…")

        def _run():
            import threading
            errors = []
            for mod in self._STARTER_MODS:
                try:
                    # Pobierz najnowszy plik dla Fabric 1.21.1
                    url = (f"https://api.modrinth.com/v2/project/{mod['id']}"
                           f"/version?loaders=[\"fabric\"]&game_versions=[\"1.21.1\"]")
                    r = requests.get(url, timeout=10)
                    versions = r.json()
                    if not versions:
                        errors.append(mod["name"])
                        continue
                    file_url = versions[0]["files"][0]["url"]
                    filename = versions[0]["files"][0]["filename"]
                    dest = mods_dir / filename
                    if dest.exists():
                        continue
                    data = requests.get(file_url, timeout=30).content
                    dest.write_bytes(data)
                except Exception as e:
                    errors.append(f"{mod['name']} ({e})")

            if errors:
                self.after(0, lambda: self._starter_status(
                    f"⚠ Zainstalowano z błędami: {', '.join(errors)}"))
            else:
                self.after(0, lambda: self._starter_status(
                    f"✅ Moddy Starter Pack zainstalowany w: {inst['name']}"))

        threading.Thread(target=_run, daemon=True).start()

    def _starter_status(self, msg: str):
        # Znajdź lub utwórz label statusu
        if not hasattr(self, "_starter_lbl") or not self._starter_lbl.winfo_exists():
            self._starter_lbl = ctk.CTkLabel(
                self._packs_scroll, text="",
                font=ctk.CTkFont(size=11), text_color="#888")
            self._starter_lbl.grid(row=0, column=0, sticky="w", padx=16)
        self._starter_lbl.configure(text=msg)

    # ── helpers ───────────────────────────────────────────────────────────────

    def on_show(self, **_):
        self._refresh_my_packs()
        self._refresh_creator_installations()

    def _refresh_creator_installations(self):
        installations = load_installations()
        names = [i.get("name", "?") for i in installations]
        if not names:
            names = ["Brak instalacji"]
        self._create_inst_menu.configure(values=names)
        self._create_inst_var.set(names[0])
        if installations:
            self._on_creator_inst_change(names[0])

    def _get_installation_by_name(self, name: str) -> dict | None:
        for inst in load_installations():
            if inst.get("name") == name:
                return inst
        return None
