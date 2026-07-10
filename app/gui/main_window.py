"""
Moddy Launcher – główne okno.
Layout:
  ┌──────────┬──────────────────────────────┐
  │ Sidebar  │        Content (strony)       │
  │ Logo     │                               │
  │ Konta    │                               │
  │ Nawigacja│                               │
  └──────────┴──────────────────────────────┘
  │  📦 Mody  │  🎮 Instalacja ▼  │  👤 Konto ▼  │  ▶ GRAJ  │
  └──────────────────────────────────────────────────────────┘
"""
import tkinter as tk
import customtkinter as ctk
import threading
import time
from datetime import datetime

from ..core.mod_library import load_installations, save_installations, load_settings
from ..core.accounts_manager import (
    get_selected_account, get_accounts, set_selected
)
from ..core.minecraft_launcher import (
    is_installed, install_version, launch, get_instance_dir
)
from ..core.modpack_manager import download_modpack_mods
from ..auth.token_store import load_session, clear_session, is_premium
from .pages.home_page import HomePage
from .pages.wizard_page import WizardPage
from .pages.browser_page import BrowserPage
from .pages.detail_page import DetailPage
from .pages.library_page import LibraryPage
from .pages.settings_page import SettingsPage
from .pages.login_page import LoginPage
from .pages.accounts_page import AccountsPage
from .pages.modpacks_page import ModpacksPage
from .pages.integrations_page import IntegrationsPage
from .pages.ai_generator_page import AIGeneratorPage
from .pages.premium_page import PremiumPage
from .pages.cosmetics_page import CosmeticsPage
from .components.integration_bar import IntegrationBar
from ..core.integrity_checker import register_file
from .splash import SplashScreen


def _fmt_eta(secs: float) -> str:
    s = int(max(secs, 0))
    if s >= 3600:
        return f"{s // 3600}g {(s % 3600) // 60}m"
    if s >= 60:
        return f"{s // 60}m {s % 60}s"
    return f"{s}s"


class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.withdraw()  # Ukryj do czasu załadowania

        settings = load_settings()
        ctk.set_appearance_mode(settings.get("theme", "dark"))
        ctk.set_default_color_theme("dark-blue")
        self.title("Moddy – Minecraft Launcher")
        self.geometry("1000x660")
        self.minsize(800, 520)

        # Splash screen
        self._splash: SplashScreen | None = None
        try:
            self._splash = SplashScreen(self)
            self._splash.set_status("Ładowanie…")
            self._splash.set_progress(0.15)
        except Exception:
            pass

        self._installations: list[dict] = load_installations()
        self._selected_inst: dict | None = (
            self._installations[0] if self._installations else None
        )
        self._history: list[tuple[str, dict]] = []
        self._current_page: ctk.CTkFrame | None = None
        self._user_info: dict | None = None
        self._token: str | None = None
        self._installing = False
        self._install_status_msg = ""
        self._install_start_time = 0.0
        self._install_progress_val = 0
        self._max_val = 1
        self._last_ui_update = 0.0
        self._after_install_tick: str | None = None
        self._acc_popup: tk.Toplevel | None = None
        self._overlay_listener = None

        # Integracje – None do czasu inicjalizacji w tle
        self._obs     = None
        self._spotify = None
        self._discord = None
        self._monitor = None

        if self._splash:
            self._splash.set_progress(0.4)
            self._splash.set_status("Budowanie interfejsu…")

        self._build()

        if self._splash:
            self._splash.set_progress(0.85)
            self._splash.set_status("Gotowe!")

        # Pokaż okno po krótkim opóźnieniu (pozwól splash na renderowanie)
        self.after(350, self._finish_startup)

        # Integracje w tle (OBS, Spotify, Discord, Monitor)
        threading.Thread(target=self._init_integrations, daemon=True).start()

        # Sprawdź aktualizacje w tle (po 5 s, żeby nie spowalniać startu)
        self.after(5000, lambda: threading.Thread(
            target=self._check_update_bg, daemon=True).start())

    # ══════════════════════════════════════════════════════════════════════════
    #  BUILD
    # ══════════════════════════════════════════════════════════════════════════

    def _build(self):
        # 1) Bottom bar – pakujemy PIERWSZY żeby był zawsze na dole
        self._bottom_bar = ctk.CTkFrame(self, height=64, corner_radius=0,
                                         fg_color="#111111")
        self._bottom_bar.pack(side="bottom", fill="x")
        self._bottom_bar.pack_propagate(False)
        self._build_bottom_bar()

        # 1b) Pasek integracji (nad dolnym paskiem)
        self._int_bar = IntegrationBar(self)
        self._int_bar.pack(side="bottom", fill="x")

        # 2) Główny rząd: sidebar + content
        self._main_row = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self._main_row.pack(fill="both", expand=True)

        # Sidebar
        self._sidebar = ctk.CTkFrame(self._main_row, width=175, corner_radius=0,
                                      fg_color="#161616")
        self._sidebar.pack(side="left", fill="y")
        self._sidebar.pack_propagate(False)
        self._build_sidebar()

        # Content
        self._content = ctk.CTkFrame(self._main_row, corner_radius=0,
                                      fg_color="#1a1a1a")
        self._content.pack(side="left", fill="both", expand=True)

        # Strony
        nav = self.navigate
        self._pages: dict[str, ctk.CTkFrame] = {
            "home":     HomePage(self._content, navigate=nav,
                                 get_installations=lambda: self._installations,
                                 save_installations=self._save_installations,
                                 on_select=self._select_installation),
            "wizard":   WizardPage(self._content, navigate=nav,
                                   on_create=self._create_installation),
            "browser":  BrowserPage(self._content, navigate=nav),
            "detail":   DetailPage(self._content, navigate=nav),
            "library":  LibraryPage(self._content, navigate=nav),
            "settings": SettingsPage(self._content, navigate=nav),
            "login":    LoginPage(self._content, navigate=nav,
                                  on_logged_in=self._on_logged_in),
            "accounts": AccountsPage(self._content, navigate=nav,
                                     on_change=self._refresh_account_ui),
            "modpacks":     ModpacksPage(self._content, navigate=nav,
                                         on_install_modpack=self._install_modpack),
            "integrations": IntegrationsPage(self._content, navigate=nav,
                                             obs=None, spotify=None, discord=None),
            "ai_generator": AIGeneratorPage(
                self._content, navigate=nav,
                get_active_installation=lambda: self._selected_inst,
                on_search_mod=lambda m: self.navigate(
                    "browser", loader=self._selected_inst.get("loader", "") if self._selected_inst else "",
                    game_version=(self._selected_inst.get("version") or "") if self._selected_inst else ""
                )),
            "cosmetics":    CosmeticsPage(self._content, navigate=nav),
            "premium":      PremiumPage(
                self._content, navigate=nav,
                get_active_installation=lambda: self._selected_inst,
                resource_monitor=None,
                get_user_info=lambda: self._user_info,
                on_tier_change=self._refresh_tier_badge),
        }

        # Sesja premium
        token, user = load_session()
        if token and user:
            self._apply_user(token, user)

        self.navigate("home")

    # ══════════════════════════════════════════════════════════════════════════
    #  STARTUP
    # ══════════════════════════════════════════════════════════════════════════

    def _finish_startup(self):
        if self._splash:
            self._splash.close()
            self._splash = None
        self.deiconify()

    def _check_update_bg(self):
        """Sprawdza GitHub Releases w tle."""
        try:
            from ..core.updater import check_for_update
            info = check_for_update(timeout=8)
            if info:
                self.after(0, lambda: self._show_update_bar(info))
        except Exception:
            pass

    def _show_update_bar(self, info: dict):
        """Pokazuje pasek aktualizacji nad dolnym barem."""
        if not self.winfo_exists():
            return
        bar = ctk.CTkFrame(self, height=36, corner_radius=0, fg_color="#1a3a1a")
        bar.pack(side="bottom", fill="x", before=self._bottom_bar)
        bar.pack_propagate(False)
        ctk.CTkLabel(bar,
                     text=f"🔄  Dostępna aktualizacja {info['version']}",
                     font=ctk.CTkFont(size=11), text_color="#4CAF50").pack(
            side="left", padx=12)
        ctk.CTkButton(bar, text="Zaktualizuj teraz", height=26, width=130,
                      fg_color="#4CAF50", hover_color="#388E3C",
                      font=ctk.CTkFont(size=11),
                      command=lambda: self._do_update(info, bar)).pack(
            side="left", padx=4, pady=5)
        ctk.CTkButton(bar, text="✕", width=28, height=26,
                      fg_color="transparent", hover_color="#2a2a2a",
                      text_color="#666",
                      command=bar.destroy).pack(side="right", padx=8, pady=5)

    def _do_update(self, info: dict, bar: ctk.CTkFrame):
        from ..core.updater import download_and_install
        lbl = ctk.CTkLabel(bar, text="⏳ Pobieranie…",
                            font=ctk.CTkFont(size=11), text_color="#888")
        lbl.pack(side="left", padx=8)

        def _progress(done: int, total: int):
            if total:
                pct = int(done / total * 100)
                self.after(0, lambda: lbl.configure(text=f"⏳ {pct}%"))

        def _done(ok: bool, msg: str):
            self.after(0, lambda: lbl.configure(
                text=f"{'✅' if ok else '❌'} {msg}",
                text_color="#4CAF50" if ok else "#FF4444"))

        download_and_install(info["url"], on_progress=_progress, on_done=_done)

    def _refresh_tier_badge(self):
        if is_premium(self._user_info):
            self._tier_lbl.configure(text="✨ Premium", text_color="#FFD700")
        else:
            self._tier_lbl.configure(text="🔒 Free", text_color="#555")

    def _start_overlay_listener(self):
        """Uruchamia listener hotkey overlay po starcie gry."""
        try:
            from ..core.game_overlay import OverlayHotkeyListener
            from ..core.mod_library import load_settings
            hotkey = load_settings().get("overlay_hotkey", "insert")
            if self._overlay_listener:
                self._overlay_listener.stop()
            self._overlay_listener = OverlayHotkeyListener(
                on_trigger=lambda: self.after(0, self._show_overlay),
                hotkey=hotkey,
            )
            self._overlay_listener.start()
        except Exception:
            pass

    def _show_overlay(self):
        from .overlay_window import ModdyOverlay
        try:
            ov = ModdyOverlay(self)
            ov.focus_force()
        except Exception:
            pass

    def _init_integrations(self):
        """Inicjalizuje OBS/Spotify/Discord/Monitor w wątku – nie blokuje GUI."""
        try:
            from ..integrations.obs_client import OBSClient
            self._obs = OBSClient()
        except Exception:
            pass
        try:
            from ..integrations.spotify_client import SpotifyClient
            self._spotify = SpotifyClient()
        except Exception:
            pass
        try:
            from ..integrations.discord_rpc import DiscordRPCClient
            self._discord = DiscordRPCClient()
            self._discord.set_callback(
                lambda s: self.after(0, lambda: self._int_bar.update_discord(s)))
        except Exception:
            pass
        try:
            from ..core.resource_monitor import ResourceMonitor
            self._monitor = ResourceMonitor()
        except Exception:
            pass

        # Aktualizuj pasek integracji i stronę integracji po inicjalizacji
        def _after():
            if self._obs:
                self._int_bar.set_obs(self._obs)
            if self._spotify:
                self._int_bar.set_spotify(self._spotify)
            # Zaktualizuj IntegrationsPage jeśli jest już zainicjalizowana
            ipage = self._pages.get("integrations")
            if ipage and hasattr(ipage, "set_clients"):
                ipage.set_clients(self._obs, self._spotify, self._discord)

        self.after(0, _after)

    # ══════════════════════════════════════════════════════════════════════════
    #  SIDEBAR
    # ══════════════════════════════════════════════════════════════════════════

    def _build_sidebar(self):
        s = self._sidebar

        # Logo
        ctk.CTkLabel(s, text="⛏ moddy",
                     font=ctk.CTkFont(size=22, weight="bold"),
                     text_color="#FF6B35").pack(pady=(18, 2))
        ctk.CTkLabel(s, text="Minecraft Launcher",
                     font=ctk.CTkFont(size=9), text_color="#444").pack(pady=(0, 10))

        ctk.CTkFrame(s, height=1, fg_color="#2a2a2a").pack(fill="x", padx=10)

        # ── Konta ─────────────────────────────────────────────────────────────
        ctk.CTkButton(s, text="👤  Zarządzaj kontami", height=30,
                      fg_color="transparent", hover_color="#2a2a2a",
                      text_color="#888", font=ctk.CTkFont(size=11),
                      anchor="w",
                      command=lambda: self.navigate("accounts")).pack(
            fill="x", padx=8, pady=(10, 2))

        ctk.CTkFrame(s, height=1, fg_color="#2a2a2a").pack(fill="x", padx=10, pady=6)

        # ── Nawigacja ─────────────────────────────────────────────────────────
        ctk.CTkLabel(s, text="NAWIGACJA",
                     font=ctk.CTkFont(size=9, weight="bold"),
                     text_color="#555").pack(anchor="w", padx=12, pady=(4, 4))

        nav_items = [
            ("🏠  Strona główna",   "home"),
            ("🤖  AI Generator",     "ai_generator"),
            ("🎒  Paczki modów",     "modpacks"),
            ("📚  Biblioteka",       "library"),
            ("🧥  Kosmetyki",        "cosmetics"),
            ("✨  Premium",          "premium"),
            ("🔌  Integracje",       "integrations"),
            ("⚙  Ustawienia",       "settings"),
        ]
        for label, page in nav_items:
            ctk.CTkButton(s, text=label, height=32,
                          fg_color="transparent", hover_color="#2a2a2a",
                          anchor="w", font=ctk.CTkFont(size=12),
                          command=lambda p=page: self.navigate(p)).pack(
                fill="x", padx=8, pady=1)

        # Przeglądarka – zawsze otwiera się z aktywną instalacją
        ctk.CTkButton(s, text="📦  Przeglądarka", height=32,
                      fg_color="transparent", hover_color="#2a2a2a",
                      anchor="w", font=ctk.CTkFont(size=12),
                      command=self._open_browser_for_active).pack(
            fill="x", padx=8, pady=1)

        ctk.CTkFrame(s, height=1, fg_color="#2a2a2a").pack(fill="x", padx=10, pady=6)

        # Wstecz
        self._back_btn = ctk.CTkButton(
            s, text="← Wstecz", height=28,
            fg_color="transparent", hover_color="#2a2a2a",
            text_color="#666", font=ctk.CTkFont(size=11), anchor="w",
            command=self._go_back, state="disabled")
        self._back_btn.pack(fill="x", padx=8)

        # Moddy premium (dół)
        ctk.CTkLabel(s, text="", fg_color="transparent").pack(expand=True)

        ctk.CTkFrame(s, height=1, fg_color="#2a2a2a").pack(fill="x", padx=10)
        self._moddy_btn = ctk.CTkButton(
            s, text="Zaloguj Moddy Premium", height=28,
            fg_color="transparent", hover_color="#2a2a2a",
            text_color="#4285F4", font=ctk.CTkFont(size=10),
            command=lambda: self.navigate("login"))
        self._moddy_btn.pack(fill="x", padx=8, pady=4)
        self._tier_lbl = ctk.CTkLabel(
            s, text="🔒 Free", font=ctk.CTkFont(size=9), text_color="#555")
        self._tier_lbl.pack(pady=(0, 6))

    def _refresh_account_ui(self):
        """Odśwież przycisk konta w dolnym pasku."""
        self._refresh_bottom_account()

    # ══════════════════════════════════════════════════════════════════════════
    #  BOTTOM BAR
    # ══════════════════════════════════════════════════════════════════════════

    def _build_bottom_bar(self):
        b = self._bottom_bar

        # Mody
        ctk.CTkButton(b, text="📦  Mody", width=90, height=40,
                      fg_color="#2a2a2a", hover_color="#FF6B35",
                      font=ctk.CTkFont(size=12),
                      command=self._open_mods).pack(side="left", padx=(12, 4), pady=12)

        # Separator
        ctk.CTkFrame(b, width=1, height=36, fg_color="#333").pack(
            side="left", padx=6, pady=14)

        # Wybór instalacji
        self._inst_var = tk.StringVar(value="Brak instalacji")
        self._inst_menu = ctk.CTkOptionMenu(
            b, variable=self._inst_var,
            values=["Brak instalacji"],
            width=220, height=40,
            fg_color="#2a2a2a", button_color="#3a3a3a",
            button_hover_color="#FF6B35",
            font=ctk.CTkFont(size=12),
            command=self._on_inst_select)
        self._inst_menu.pack(side="left", padx=4, pady=12)

        # Separator
        ctk.CTkFrame(b, width=1, height=36, fg_color="#333").pack(
            side="left", padx=6, pady=14)

        # Konto – przycisk otwierający popup
        self._acc_btn = ctk.CTkButton(
            b, text="👤  Brak konta", width=160, height=40,
            fg_color="#2a2a2a", hover_color="#3a3a3a",
            font=ctk.CTkFont(size=12), anchor="w",
            command=self._toggle_account_popup)
        self._acc_btn.pack(side="left", padx=4, pady=12)

        # PLAY button (po prawej)
        self._play_btn = ctk.CTkButton(
            b, text="▶  GRAJ", width=130, height=44,
            fg_color="#4CAF50", hover_color="#388E3C",
            font=ctk.CTkFont(size=15, weight="bold"),
            command=self._on_play)
        self._play_btn.pack(side="right", padx=16, pady=10)

        # Progress bar (ukryty na start)
        self._bottom_progress = ctk.CTkProgressBar(b, height=4, corner_radius=0)
        self._bottom_progress.place(relx=0, rely=0, relwidth=1, anchor="nw")
        self._bottom_progress.set(0)
        self._bottom_progress.place_forget()

        self._bottom_status = ctk.CTkLabel(
            b, text="", font=ctk.CTkFont(size=10), text_color="#888")
        self._bottom_status.pack(side="left", padx=8)

        # Wypełnij dane
        self._refresh_bottom_installations()
        self._refresh_bottom_account()

    def _refresh_bottom_installations(self):
        names = [i.get("name", "?") for i in self._installations]
        if not names:
            self._inst_menu.configure(values=["Brak instalacji"])
            self._inst_var.set("Brak instalacji")
            return
        self._inst_menu.configure(values=names)
        if self._selected_inst:
            self._inst_var.set(self._selected_inst.get("name", names[0]))
        else:
            self._inst_var.set(names[0])
            self._selected_inst = self._installations[0]
        self._refresh_play_btn()

    def _refresh_bottom_account(self):
        selected = get_selected_account()
        if selected:
            icon = "🎮" if selected.get("type") == "microsoft" else "👤"
            self._acc_btn.configure(text=f"{icon}  {selected['username'][:14]}")
        else:
            self._acc_btn.configure(text="👤  Brak konta")

    def _refresh_play_btn(self):
        if not self._selected_inst:
            self._play_btn.configure(
                text="Brak instalacji", state="disabled",
                fg_color="#333", hover_color="#333")
            return
        if is_installed(self._selected_inst):
            self._play_btn.configure(
                text="▶  GRAJ", state="normal",
                fg_color="#4CAF50", hover_color="#388E3C")
        else:
            self._play_btn.configure(
                text="⬇  Zainstaluj", state="normal",
                fg_color="#2196F3", hover_color="#1565C0")

    def _on_inst_select(self, name: str):
        for inst in self._installations:
            if inst.get("name") == name:
                self._selected_inst = inst
                break
        self._refresh_play_btn()
        # Też zaznacz na home page
        if hasattr(self._pages.get("home"), "set_selected"):
            self._pages["home"].set_selected(self._selected_inst)

    def _on_acc_select(self, acc_uuid: str):
        set_selected(acc_uuid)
        self._refresh_account_ui()
        self._close_account_popup()

    # ── account popup ─────────────────────────────────────────────────────────

    def _toggle_account_popup(self):
        if self._acc_popup and self._acc_popup.winfo_exists():
            self._close_account_popup()
        else:
            self._open_account_popup()

    def _close_account_popup(self):
        if self._acc_popup:
            try:
                self._acc_popup.destroy()
            except Exception:
                pass
            self._acc_popup = None

    def _open_account_popup(self):
        self._close_account_popup()

        btn  = self._acc_btn
        bx   = btn.winfo_rootx()
        by   = btn.winfo_rooty()
        pw, ph = 300, 320

        pop = tk.Toplevel(self)
        pop.overrideredirect(True)
        pop.attributes("-topmost", True)
        pop.geometry(f"{pw}x{ph}+{bx}+{by - ph - 4}")
        pop.configure(bg="#1a1a1a")
        self._acc_popup = pop

        # Zamknij przy kliknięciu poza popupem
        pop.bind("<FocusOut>", lambda e: self.after(100, self._check_popup_focus))

        # Ramka CTk wewnątrz Toplevel
        frame = ctk.CTkFrame(pop, corner_radius=12, fg_color="#1e1e1e",
                             border_width=1, border_color="#333333")
        frame.pack(fill="both", expand=True, padx=2, pady=2)

        # Nagłówek
        hdr = ctk.CTkFrame(frame, fg_color="#161616", corner_radius=0,
                           height=36)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        ctk.CTkLabel(hdr, text="👤  Konta Minecraft",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color="#888").pack(side="left", padx=12, pady=8)
        ctk.CTkButton(hdr, text="⚙", width=28, height=28,
                      fg_color="transparent", hover_color="#2a2a2a",
                      text_color="#666", font=ctk.CTkFont(size=13),
                      command=lambda: (self._close_account_popup(),
                                       self.navigate("accounts"))
                      ).pack(side="right", padx=4)

        # Lista kont
        scroll = ctk.CTkScrollableFrame(frame, fg_color="transparent",
                                        height=160, corner_radius=0)
        scroll.pack(fill="x", padx=8, pady=(6, 0))

        accounts = get_accounts()
        selected = get_selected_account()
        sel_uuid = selected["uuid"] if selected else None

        if not accounts:
            ctk.CTkLabel(scroll, text="Brak kont – dodaj poniżej",
                         font=ctk.CTkFont(size=11), text_color="#555").pack(pady=12)
        else:
            for acc in accounts:
                is_sel = acc["uuid"] == sel_uuid
                icon   = "🎮" if acc.get("type") == "microsoft" else "👤"
                fg     = "#FF6B35" if is_sel else "transparent"

                row = ctk.CTkFrame(scroll, fg_color="transparent")
                row.pack(fill="x", pady=1)

                ctk.CTkButton(
                    row,
                    text=f"{icon}  {acc['username']}",
                    height=34, anchor="w",
                    fg_color=fg,
                    hover_color="#FF6B35" if not is_sel else "#e05520",
                    font=ctk.CTkFont(size=12,
                                     weight="bold" if is_sel else "normal"),
                    command=lambda u=acc["uuid"]: self._on_acc_select(u),
                ).pack(side="left", fill="x", expand=True)

                ctk.CTkButton(
                    row,
                    text="✕", width=30, height=34,
                    fg_color="transparent", hover_color="#aa2222",
                    text_color="#555", font=ctk.CTkFont(size=12),
                    command=lambda u=acc["uuid"]: self._popup_remove_account(u),
                ).pack(side="left")

        # Separator
        ctk.CTkFrame(frame, height=1, fg_color="#2a2a2a").pack(
            fill="x", padx=8, pady=6)

        # Dodaj offline
        add_row = ctk.CTkFrame(frame, fg_color="transparent")
        add_row.pack(fill="x", padx=8)
        self._popup_entry = ctk.CTkEntry(
            add_row, placeholder_text="Nowa nazwa offline…",
            height=32, font=ctk.CTkFont(size=11))
        self._popup_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self._popup_entry.bind("<Return>", lambda e: self._popup_add_offline())
        ctk.CTkButton(
            add_row, text="+", width=32, height=32,
            fg_color="#4CAF50", hover_color="#388E3C",
            font=ctk.CTkFont(size=16),
            command=self._popup_add_offline,
        ).pack(side="left")

        # Dodaj Microsoft
        ctk.CTkButton(
            frame, text="🎮  Zaloguj Microsoft", height=32,
            fg_color="#0078D4", hover_color="#005fa3",
            font=ctk.CTkFont(size=11),
            command=lambda: (self._close_account_popup(),
                             self.navigate("accounts")),
        ).pack(fill="x", padx=8, pady=(6, 4))

        self._popup_msg = ctk.CTkLabel(
            frame, text="", font=ctk.CTkFont(size=10), text_color="#4CAF50")
        self._popup_msg.pack(pady=(0, 4))

        pop.focus_force()

    def _check_popup_focus(self):
        try:
            focused = self.focus_get()
            if (self._acc_popup and self._acc_popup.winfo_exists() and
                    focused not in (self._acc_popup,) and
                    not str(focused).startswith(str(self._acc_popup))):
                self._close_account_popup()
        except Exception:
            pass

    def _popup_remove_account(self, acc_uuid: str):
        from ..core.accounts_manager import remove_account
        remove_account(acc_uuid)
        self._refresh_account_ui()
        self._close_account_popup()
        self._open_account_popup()

    def _popup_add_offline(self):
        from ..core.accounts_manager import add_offline_account
        name = self._popup_entry.get().strip()
        try:
            add_offline_account(name)
            self._popup_entry.delete(0, "end")
            self._popup_msg.configure(text=f"✓ Dodano: {name}", text_color="#4CAF50")
            self._refresh_account_ui()
            self.after(1500, self._close_account_popup)
        except ValueError as e:
            self._popup_msg.configure(text=str(e), text_color="#FF6B35")

    def _select_installation(self, inst: dict):
        """Wywoływane przez HomePage po kliknięciu karty → otwiera przeglądarkę."""
        self._selected_inst = inst
        self._inst_var.set(inst.get("name", ""))
        self._refresh_play_btn()
        if inst:
            self.navigate("browser",
                          loader=inst.get("loader", ""),
                          game_version=(inst.get("version") or
                                        inst.get("game_version", "")))

    # ── play / install ────────────────────────────────────────────────────────

    def _open_mods(self):
        self._open_browser_for_active()

    def _open_browser_for_active(self):
        if self._selected_inst:
            self.navigate("browser",
                          loader=self._selected_inst.get("loader"),
                          game_version=(self._selected_inst.get("version") or
                                        self._selected_inst.get("game_version")))
        else:
            self.navigate("browser")

    def _on_play(self):
        if self._installing:
            return
        if not self._selected_inst:
            return
        account = get_selected_account()
        if not account:
            self.navigate("accounts")
            return
        if is_installed(self._selected_inst):
            self._do_launch()
        else:
            self._do_install()

    def _do_install(self):
        self._installing = True
        self._play_btn.configure(state="disabled", text="⬇  Instalowanie…",
                                  fg_color="#2196F3")

        inst = self._selected_inst
        self._max_val = 1
        self._install_progress_val = 0
        self._install_start_time = time.monotonic()
        self._install_status_msg = "Przygotowywanie…"
        self._last_ui_update = 0.0

        self._bottom_progress.set(0)
        self._bottom_progress.place(relx=0, rely=0, relwidth=1, anchor="nw")
        self._bottom_status.configure(text="⬇ Przygotowywanie…", text_color="#2196F3")
        self._start_install_tick()

        def set_status(s: str):
            self._install_status_msg = s

        def set_max(m: int):
            self._max_val = max(m, 1)

        def set_progress(p: int):
            self._install_progress_val = p
            now = time.monotonic()
            if now - self._last_ui_update < 0.05:
                return
            self._last_ui_update = now
            frac = min(p / self._max_val, 1.0)
            self.after(0, lambda f=frac: self._bottom_progress.set(f))

        cb = {"setStatus": set_status, "setMax": set_max, "setProgress": set_progress}

        def _worker():
            try:
                install_version(inst, callback=cb)
                inst["installed"] = True
                save_installations(self._installations)
                self.after(0, self._on_install_success)
            except Exception as e:
                err = str(e)
                self.after(0, lambda m=err: self._on_install_error(m))

        threading.Thread(target=_worker, daemon=True).start()

    def _do_launch(self):
        account = get_selected_account()
        if not account:
            return
        inst = self._selected_inst
        self._play_btn.configure(state="disabled", text="Uruchamianie…",
                                  fg_color="#388E3C")
        try:
            launch(
                inst, account,
                on_start=lambda: self.after(0, self._on_game_started),
                on_stop=lambda: self.after(0, self._on_game_stopped),
            )
        except RuntimeError as e:
            err = str(e)
            self.after(0, lambda m=err: self._bottom_status.configure(
                text=f"❌ {m}", text_color="#FF4444"))
            self.after(0, lambda: self._play_btn.configure(
                state="normal", text="▶  GRAJ", fg_color="#4CAF50"))

    def _on_game_started(self):
        self._play_btn.configure(text="🎮  Gram…", fg_color="#388E3C",
                                  state="disabled")
        self._bottom_status.configure(text="Gra uruchomiona", text_color="#4CAF50")
        self._start_overlay_listener()
        # Discord RPC
        if self._discord and self._discord.connected and self._selected_inst:
            self._discord.set_presence_playing(self._selected_inst)
        s = load_settings()
        if self._obs and s.get("obs_auto_record") and self._obs.status.connected:
            self._obs.start_recording()

    def _on_game_stopped(self):
        self._play_btn.configure(state="normal", text="▶  GRAJ",
                                  fg_color="#4CAF50", hover_color="#388E3C")
        self._bottom_status.configure(text="", text_color="#888")
        # Discord RPC
        if self._discord and self._discord.connected:
            self._discord.set_presence_idle()
        s = load_settings()
        if self._obs and s.get("obs_auto_stop") and self._obs.status.recording:
            self._obs.stop_recording()

    # ── install progress (bottom bar) ─────────────────────────────────────────

    def _start_install_tick(self):
        self._after_install_tick = self.after(400, self._install_tick)

    def _install_tick(self):
        if not self._installing:
            return
        elapsed = max(time.monotonic() - self._install_start_time, 0.1)
        frac = min(self._install_progress_val / max(self._max_val, 1), 1.0)
        parts = [f"⬇ {self._install_status_msg}"]
        if frac > 0.02 and elapsed > 1.0:
            speed = self._install_progress_val / elapsed
            parts.append(f"{speed:.1f} pl/s")
            if frac < 0.999:
                eta = elapsed / frac * (1.0 - frac)
                parts.append(f"~{_fmt_eta(eta)}")
        self._bottom_status.configure(text="  •  ".join(parts), text_color="#2196F3")
        self._after_install_tick = self.after(400, self._install_tick)

    def _stop_install_tick(self):
        if self._after_install_tick:
            self.after_cancel(self._after_install_tick)
            self._after_install_tick = None

    def _on_install_success(self):
        self._installing = False
        self._stop_install_tick()
        self._bottom_progress.set(1.0)
        self.after(300, lambda: self._bottom_progress.place_forget())
        self._refresh_play_btn()
        self._bottom_status.configure(text="✓ Zainstalowano!", text_color="#4CAF50")
        self.after(3000, lambda: self._bottom_status.configure(text="", text_color="#888"))
        self._do_launch()

    def _on_install_error(self, msg: str):
        self._installing = False
        self._stop_install_tick()
        self._bottom_progress.place_forget()
        short = msg[:100]
        self._bottom_status.configure(text=f"❌ {short}", text_color="#FF4444")
        self.after(8000, lambda: self._bottom_status.configure(text="", text_color="#888"))
        self._play_btn.configure(state="normal", text="⬇  Zainstaluj",
                                  fg_color="#2196F3", hover_color="#1565C0")

    # ── modpack install ───────────────────────────────────────────────────────

    def _install_modpack(self, pack: dict):
        """
        Instaluje paczkę modów:
          Faza 1 – pobiera Minecraft + mod loader
          Faza 2 – pobiera mody do katalogu instancji
        """
        if self._installing:
            return
        self._installing = True

        inst = {
            "name":           pack.get("name", "Paczka"),
            "loader":         pack.get("loader", "vanilla"),
            "version":        pack.get("minecraft_version", ""),
            "loader_version": pack.get("loader_version"),
            "memory_mb":      pack.get("memory_mb", 2048),
            "installed":      False,
            "created":        datetime.now().isoformat(),
        }
        settings = load_settings()
        if settings.get("java_path"):
            inst["java_path"] = settings["java_path"]

        self._installations.append(inst)
        save_installations(self._installations)
        self._selected_inst = inst
        self._refresh_bottom_installations()
        self._pages["home"].on_show()

        n_mods = len(pack.get("mods", []))

        # Start bottom bar
        self._max_val = 1
        self._install_progress_val = 0
        self._install_start_time = time.monotonic()
        self._install_status_msg = "[1/2] Pobieranie Minecraft…"
        self._last_ui_update = 0.0

        self._bottom_progress.set(0)
        self._bottom_progress.place(relx=0, rely=0, relwidth=1, anchor="nw")
        self._play_btn.configure(state="disabled", text="⬇  Instalowanie…",
                                  fg_color="#2196F3")
        self._start_install_tick()

        def set_status(s: str):
            self._install_status_msg = f"[1/2] {s}"

        def set_max(m: int):
            self._max_val = max(m, 1)

        def set_progress(p: int):
            self._install_progress_val = p
            now = time.monotonic()
            if now - self._last_ui_update < 0.05:
                return
            self._last_ui_update = now
            frac = min(p / self._max_val, 1.0)
            self.after(0, lambda f=frac: self._bottom_progress.set(f))

        mc_cb = {"setStatus": set_status, "setMax": set_max, "setProgress": set_progress}

        def _worker():
            # ── Faza 1: Minecraft + loader ────────────────────────────────
            try:
                install_version(inst, callback=mc_cb)
            except Exception as e:
                err = str(e)
                self.after(0, lambda m=err: self._on_modpack_error(m))
                return

            inst["installed"] = True
            save_installations(self._installations)

            # ── Faza 2: Mody ──────────────────────────────────────────────
            self._install_status_msg = "[2/2] Pobieranie modów…"
            self._install_start_time = time.monotonic()
            self._install_progress_val = 0
            self._max_val = 1
            self.after(0, lambda: self._bottom_progress.set(0))

            instance_mods = get_instance_dir(inst) / "mods"
            settings_local = load_settings()

            def _mod_status(s: str):
                self._install_status_msg = f"[2/2] {s}"

            def _mod_progress(p: float):
                now = time.monotonic()
                if now - self._last_ui_update < 0.05:
                    return
                self._last_ui_update = now
                self.after(0, lambda f=p: self._bottom_progress.set(f))

            ok, errors = download_modpack_mods(
                pack, instance_mods, settings_local,
                on_status=_mod_status,
                on_progress=_mod_progress,
            )

            self.after(0, lambda: self._on_modpack_done(ok, errors, n_mods))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_modpack_done(self, ok: int, errors: list, total: int):
        self._installing = False
        self._stop_install_tick()
        self._bottom_progress.set(1.0)
        self.after(300, lambda: self._bottom_progress.place_forget())
        self._refresh_play_btn()

        msg = f"✓ Zainstalowano! {ok}/{total} modów"
        if errors:
            skipped = "; ".join(errors[:2])
            suffix = f" i {len(errors) - 2} więcej" if len(errors) > 2 else ""
            msg += f"  •  pominięto: {skipped}{suffix}"
        self._bottom_status.configure(text=msg, text_color="#4CAF50")
        self.after(7000, lambda: self._bottom_status.configure(text="", text_color="#888"))

    def _on_modpack_error(self, msg: str):
        self._installing = False
        self._stop_install_tick()
        self._bottom_progress.place_forget()
        short = msg[:100]
        self._bottom_status.configure(text=f"❌ {short}", text_color="#FF4444")
        self.after(8000, lambda: self._bottom_status.configure(text="", text_color="#888"))
        self._play_btn.configure(state="normal", text="⬇  Zainstaluj",
                                  fg_color="#2196F3")

    # ══════════════════════════════════════════════════════════════════════════
    #  AUTH (Moddy Premium)
    # ══════════════════════════════════════════════════════════════════════════

    def _on_logged_in(self, token, user_info):
        self._apply_user(token, user_info)
        self.navigate("home")

    def _apply_user(self, token, user_info):
        self._token = token
        self._user_info = user_info
        self._pages["browser"].set_user(user_info)
        self._pages["detail"].set_user(user_info)
        # Odśwież bramkę premium jeśli strona była już widoczna
        if hasattr(self._pages.get("premium"), "on_show"):
            self._pages["premium"].on_show()
        if user_info:
            name = user_info.get("username", "Użytkownik")
            self._moddy_btn.configure(
                text=f"✓ {name}", text_color="#FF6B35",
                command=self._logout)
        else:
            self._moddy_btn.configure(
                text="Zaloguj Moddy Premium", text_color="#4285F4",
                command=lambda: self.navigate("login"))
        self._refresh_tier_badge()

    def _logout(self):
        clear_session()
        self._apply_user(None, None)

    # ══════════════════════════════════════════════════════════════════════════
    #  NAVIGATION
    # ══════════════════════════════════════════════════════════════════════════

    def navigate(self, page: str, _push_history: bool = True, **kwargs):
        if self._current_page is not None:
            self._current_page.pack_forget()

        target = self._pages[page]
        if hasattr(target, "on_show"):
            target.on_show(**kwargs)

        target.pack(fill="both", expand=True)
        self._current_page = target

        if page == "accounts":
            self.after(300, self._refresh_account_ui)

        if _push_history and page not in ("home", "login"):
            self._history.append((page, kwargs))
        elif page in ("home", "login"):
            self._history.clear()

        self._back_btn.configure(
            state="normal" if self._history and page not in ("home", "login")
            else "disabled")

    def _go_back(self):
        if not self._history:
            return
        self._history.pop()
        if self._history:
            p, kw = self._history[-1]
            self.navigate(p, _push_history=False, **kw)
        else:
            self.navigate("home", _push_history=False)

    # ══════════════════════════════════════════════════════════════════════════
    #  INSTALLATIONS
    # ══════════════════════════════════════════════════════════════════════════

    def _save_installations(self, installations: list):
        self._installations = installations
        save_installations(installations)
        self._refresh_bottom_installations()

    def _create_installation(self, name: str, loader: str, version: str,
                              memory_mb: int = 2048,
                              loader_ver: str | None = None):
        settings = load_settings()
        inst = {
            "name": name,
            "loader": loader.lower(),
            "version": version,
            "loader_version": loader_ver,
            "memory_mb": memory_mb,
            "java_path": settings.get("java_path", ""),
            "installed": False,
            "created": datetime.now().isoformat(),
        }
        self._installations.append(inst)
        save_installations(self._installations)
        self._selected_inst = inst
        self._refresh_bottom_installations()
        self._pages["home"].on_show()
        # Przejdź od razu do przeglądarki modów dla tej wersji
        self.navigate("browser",
                      loader=inst["loader"],
                      game_version=inst["version"])
