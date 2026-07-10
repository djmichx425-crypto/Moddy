"""
Marketplace — sklep społeczności Moddy.
Modpacki, shadery, resource packi, profile PvP/FPS.
"""
import threading
import customtkinter as ctk
import requests

from ...core.mod_library import load_settings


# Wbudowane kategorie z przykładowymi wpisami (zastąp API gdy backend gotowy)
MARKETPLACE_DATA = {
    "🎒 Modpacki": [
        {"name": "FPS Booster Pack",   "author": "ModdyCommunity",
         "desc": "Sodium, Lithium, Starlight, FerriteCore — +100 FPS",
         "tags": ["FPS", "Optymalizacja"], "downloads": 15420,
         "mods": ["Sodium", "Lithium", "Starlight", "FerriteCore", "EntityCulling"],
         "loader": "fabric", "mc_version": "1.20.1"},
        {"name": "Magic & RPG",         "author": "WizardDev",
         "desc": "Botania, Ars Nouveau, Iron's Spells — pełne RPG",
         "tags": ["RPG", "Magia"], "downloads": 8930,
         "mods": ["Botania", "Ars Nouveau", "Iron's Spells"],
         "loader": "fabric", "mc_version": "1.20.1"},
        {"name": "Tech Automation",     "author": "TechForge",
         "desc": "Create, Applied Energistics 2, Thermal — automatyzacja",
         "tags": ["Tech", "Automatyzacja"], "downloads": 12100,
         "mods": ["Create", "Applied Energistics 2", "Thermal Expansion"],
         "loader": "forge", "mc_version": "1.20.1"},
        {"name": "Survival Realism",    "author": "SurvivalPro",
         "desc": "TerraFirmaCraft feel — realistyczne przetrwanie",
         "tags": ["Survival", "Realizm"], "downloads": 6700,
         "mods": ["Serene Seasons", "Alex's Mobs", "Farmer's Delight"],
         "loader": "fabric", "mc_version": "1.20.1"},
    ],
    "🎨 Resource Packi": [
        {"name": "Faithful 64x",        "author": "Faithful Team",
         "desc": "Wierne odwzorowanie waniliowego stylu w 64x",
         "tags": ["Tekstury", "Faithful"], "downloads": 980000,
         "mods": [], "loader": "", "mc_version": "1.20"},
        {"name": "Chroma Hills",         "author": "SapixGames",
         "desc": "Klimatyczny pack RPG z kreskówkowym stylem",
         "tags": ["RPG", "Klimat"], "downloads": 420000,
         "mods": [], "loader": "", "mc_version": "1.20"},
    ],
    "💡 Shadery": [
        {"name": "Complementary Reimagined", "author": "EminGT",
         "desc": "Najlepszy balans wydajności i wyglądu",
         "tags": ["Shadery", "Balanced"], "downloads": 5200000,
         "mods": ["Iris Shaders"], "loader": "fabric", "mc_version": "1.20"},
        {"name": "BSL Shaders",           "author": "CaptTatsu",
         "desc": "Klasyczne, piękne, sprawdzone",
         "tags": ["Shadery", "Klasyczne"], "downloads": 8700000,
         "mods": ["Iris Shaders"], "loader": "fabric", "mc_version": "1.20"},
    ],
    "⚔ Profile PvP": [
        {"name": "HyPixel PvP Setup",   "author": "PvPMaster",
         "desc": "OptiFine + BetterSprint + Keystrokes — gotowy do PvP",
         "tags": ["PvP", "HyPixel"], "downloads": 34000,
         "mods": ["Sodium", "Keystrokes Mod"], "loader": "fabric", "mc_version": "1.8.9"},
        {"name": "Crystal PvP",          "author": "CrystalDev",
         "desc": "Crystal PvP optimized — 1.20+ end crystal fights",
         "tags": ["PvP", "Crystal"], "downloads": 8900,
         "mods": ["Sodium", "Lithium", "Immediatelyfast"],
         "loader": "fabric", "mc_version": "1.20.1"},
    ],
    "🚀 Profile FPS": [
        {"name": "Ultra FPS 1.20",       "author": "FPSGod",
         "desc": "Maksymalna wydajność — 300+ FPS na każdym PC",
         "tags": ["FPS", "Ultra"], "downloads": 45000,
         "mods": ["Sodium", "Lithium", "Phosphor", "FerriteCore",
                  "EntityCulling", "LazyDFU", "Starlight"],
         "loader": "fabric", "mc_version": "1.20.1"},
    ],
}


class MarketplacePage(ctk.CTkFrame):

    def __init__(self, parent, navigate,
                 on_install_modpack=None,
                 get_selected_inst=None,
                 **kwargs):
        super().__init__(parent, corner_radius=0, fg_color="#1a1a1a", **kwargs)
        self._navigate          = navigate
        self._on_install        = on_install_modpack
        self._get_inst          = get_selected_inst
        self._active_category   = list(MARKETPLACE_DATA.keys())[0]
        self._build()

    # ── build ─────────────────────────────────────────────────────────────────

    def _build(self):
        top = ctk.CTkFrame(self, fg_color="#1e1e1e", corner_radius=0)
        top.pack(fill="x")
        ctk.CTkLabel(top, text="🛍  Marketplace",
                     font=ctk.CTkFont(size=17, weight="bold")).pack(
            side="left", padx=20, pady=13)
        ctk.CTkLabel(top, text="Paczki społeczności Moddy",
                     font=ctk.CTkFont(size=10), text_color="#555").pack(
            side="left", padx=4)

        # Kategorie (poziomy pasek)
        self._cat_frame = ctk.CTkFrame(self, fg_color="#161616", corner_radius=0)
        self._cat_frame.pack(fill="x")
        self._cat_btns: dict[str, ctk.CTkButton] = {}
        for cat in MARKETPLACE_DATA:
            btn = ctk.CTkButton(
                self._cat_frame, text=cat, height=34,
                fg_color="#FF6B35" if cat == self._active_category else "transparent",
                hover_color="#FF6B35",
                font=ctk.CTkFont(size=12),
                command=lambda c=cat: self._set_category(c))
            btn.pack(side="left", padx=4, pady=6)
            self._cat_btns[cat] = btn

        # Kontent
        self._content = ctk.CTkScrollableFrame(
            self, corner_radius=0, fg_color="transparent")
        self._content.pack(fill="both", expand=True, padx=16, pady=10)
        self._content.columnconfigure((0, 1), weight=1)

        self._render_category()

    # ── on_show ───────────────────────────────────────────────────────────────

    def on_show(self, **_):
        self._render_category()

    # ── category ──────────────────────────────────────────────────────────────

    def _set_category(self, cat: str):
        self._active_category = cat
        for c, btn in self._cat_btns.items():
            btn.configure(fg_color="#FF6B35" if c == cat else "transparent")
        self._render_category()

    def _render_category(self):
        for w in self._content.winfo_children():
            w.destroy()

        items = MARKETPLACE_DATA.get(self._active_category, [])
        for i, item in enumerate(items):
            col = i % 2
            row = i // 2
            self._make_card(item, row, col)

    def _make_card(self, item: dict, row: int, col: int):
        TAG_COLORS = {
            "FPS": "#4CAF50", "Optymalizacja": "#4CAF50",
            "RPG": "#9C27B0", "Magia": "#9C27B0",
            "Tech": "#2196F3", "Automatyzacja": "#2196F3",
            "Survival": "#FF9800", "Realizm": "#FF9800",
            "PvP": "#F44336", "Shadery": "#00BCD4",
            "Tekstury": "#FF6B35", "Klimat": "#FF6B35",
        }
        loader      = item.get("loader", "")
        mc_ver      = item.get("mc_version", "")
        n_mods      = len(item.get("mods", []))
        downloads   = item.get("downloads", 0)

        card = ctk.CTkFrame(self._content, corner_radius=12, height=220)
        card.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
        card.grid_propagate(False)

        # Header
        hdr = ctk.CTkFrame(card, corner_radius=0, fg_color="#1e1e1e",
                            height=40, corner_radius=12)
        hdr.pack(fill="x")
        ctk.CTkLabel(hdr, text=item["name"],
                     font=ctk.CTkFont(size=13, weight="bold"),
                     anchor="w").pack(side="left", padx=12, pady=10)

        dl_str = f"{downloads//1000}K" if downloads >= 1000 else str(downloads)
        ctk.CTkLabel(hdr, text=f"⬇ {dl_str}",
                     font=ctk.CTkFont(size=9), text_color="#666").pack(
            side="right", padx=8)

        # Tags
        tags_row = ctk.CTkFrame(card, fg_color="transparent")
        tags_row.pack(fill="x", padx=10, pady=(6, 0))
        for tag in item.get("tags", [])[:3]:
            c = TAG_COLORS.get(tag, "#555")
            ctk.CTkLabel(tags_row, text=tag,
                         font=ctk.CTkFont(size=9), text_color=c,
                         fg_color=c + "22", corner_radius=4,
                         width=60, height=18).pack(side="left", padx=2)

        # Opis
        ctk.CTkLabel(card, text=item["desc"],
                     font=ctk.CTkFont(size=11), text_color="#aaa",
                     wraplength=240, justify="left", anchor="w").pack(
            fill="x", padx=12, pady=(4, 0))

        # Info
        info_parts = []
        if loader:     info_parts.append(loader.capitalize())
        if mc_ver:     info_parts.append(f"MC {mc_ver}")
        if n_mods > 0: info_parts.append(f"{n_mods} modów")
        ctk.CTkLabel(card, text="  •  ".join(info_parts),
                     font=ctk.CTkFont(size=9), text_color="#555").pack(
            anchor="w", padx=12)

        # Przycisk
        btn_row = ctk.CTkFrame(card, fg_color="transparent")
        btn_row.pack(fill="x", padx=10, side="bottom", pady=8)

        ctk.CTkButton(btn_row, text="▶  Zainstaluj jednym kliknięciem",
                      height=32, fg_color="#FF6B35", hover_color="#e05520",
                      font=ctk.CTkFont(size=11),
                      command=lambda i=item: self._install(i)).pack(
            side="left", fill="x", expand=True, padx=(0, 4))

        ctk.CTkButton(btn_row, text="🔍", width=32, height=32,
                      fg_color="#2a2a2a", hover_color="#555",
                      command=lambda i=item: self._browse(i)).pack(side="left")

    # ── actions ───────────────────────────────────────────────────────────────

    def _install(self, item: dict):
        """Konwertuje wpis marketplace na paczkę i instaluje."""
        inst = self._get_inst() if self._get_inst else None
        mc_ver  = item.get("mc_version") or (inst.get("version") if inst else "1.20.1")
        loader  = item.get("loader") or (inst.get("loader") if inst else "fabric")
        mods    = [{"name": m, "source": "modrinth", "mod_id": "",
                    "filename": "", "download_url": ""}
                   for m in item.get("mods", [])]
        pack = {
            "format":            "moddy-pack-1",
            "name":              item["name"],
            "version":           "1.0.0",
            "description":       item["desc"],
            "author":            item.get("author", "Marketplace"),
            "minecraft_version": mc_ver,
            "loader":            loader,
            "loader_version":    None,
            "memory_mb":         3072,
            "mods":              mods,
        }
        if self._on_install:
            self._on_install(pack)
        else:
            self._navigate("modpacks")

    def _browse(self, item: dict):
        """Szuka modów z paczki w przeglądarce."""
        inst = self._get_inst() if self._get_inst else None
        self._navigate(
            "browser",
            loader=(item.get("loader") or (inst.get("loader") if inst else "")),
            game_version=(item.get("mc_version") or
                          (inst.get("version") if inst else "")))
