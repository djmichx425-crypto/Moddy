"""
Dynamiczny dashboard — strona główna launchera.
Pokazuje: aktywna instalacja, czas gry, ostatnia sesja,
          status serwerów, aktualizacje modów, aktualności.
"""
import tkinter as tk
import customtkinter as ctk
import threading
import time

from ...core.play_time_tracker import (
    get_total_playtime, get_recent_sessions, get_installation_stats
)
from ...core.mod_library import load_installations, load_meta
from ...core.server_manager import get_servers, ping_all_async, ServerStatus


class DashboardPage(ctk.CTkFrame):

    def __init__(self, parent, navigate,
                 get_selected_inst=None,
                 get_user_info=None,
                 on_play=None,
                 **kwargs):
        super().__init__(parent, corner_radius=0, fg_color="#1a1a1a", **kwargs)
        self._navigate       = navigate
        self._get_inst       = get_selected_inst
        self._get_user       = get_user_info
        self._on_play        = on_play
        self._server_status: dict[int, ServerStatus] = {}
        self._build()

    # ── build ─────────────────────────────────────────────────────────────────

    def _build(self):
        # Pasek powitalny
        self._top = ctk.CTkFrame(self, fg_color="#1e1e1e", corner_radius=0, height=56)
        self._top.pack(fill="x")
        self._top.pack_propagate(False)

        self._welcome = ctk.CTkLabel(
            self._top, text="⛏  Moddy Launcher",
            font=ctk.CTkFont(size=17, weight="bold"))
        self._welcome.pack(side="left", padx=20, pady=14)

        self._time_lbl = ctk.CTkLabel(
            self._top, text="",
            font=ctk.CTkFont(size=10), text_color="#555")
        self._time_lbl.pack(side="right", padx=16)

        # Główny scroll
        self._scroll = ctk.CTkScrollableFrame(
            self, corner_radius=0, fg_color="transparent")
        self._scroll.pack(fill="both", expand=True, padx=16, pady=10)
        self._scroll.columnconfigure(0, weight=1)

    # ── on_show ───────────────────────────────────────────────────────────────

    def on_show(self, **_):
        for w in self._scroll.winfo_children():
            w.destroy()

        user = self._get_user() if self._get_user else None
        name = user.get("username", "Graczu") if user else "Graczu"
        self._welcome.configure(text=f"⛏  Cześć, {name}!")
        self._time_lbl.configure(text=f"Łączny czas gry: {get_total_playtime()}")

        inst = self._get_inst() if self._get_inst else None

        row = 0
        row = self._section_active(row, inst)
        row = self._section_stats(row)
        row = self._section_servers(row)
        row = self._section_recent_sessions(row)
        row = self._section_news(row)

    # ── sekcja: aktywna instalacja + PLAY ────────────────────────────────────

    def _section_active(self, row: int, inst: dict | None) -> int:
        LOADER_COLORS = {
            "vanilla": "#4CAF50", "fabric": "#7EB5D6", "forge": "#A0522D",
            "quilt": "#9370DB", "neoforge": "#FF8C00",
        }
        card = ctk.CTkFrame(self._scroll, corner_radius=14,
                            border_width=2, border_color="#FF6B35")
        card.grid(row=row, column=0, sticky="ew", pady=(0, 10))
        card.columnconfigure(1, weight=1)

        if inst:
            loader   = (inst.get("loader") or "vanilla").lower()
            color    = LOADER_COLORS.get(loader, "#555")
            ver      = inst.get("version") or inst.get("game_version", "?")
            stats    = get_installation_stats(inst.get("name", ""))
            installed = self._is_installed(inst)

            # Badge
            badge = ctk.CTkFrame(card, fg_color="transparent", width=90)
            badge.grid(row=0, column=0, rowspan=3, padx=(14, 8), pady=12, sticky="ns")
            badge.pack_propagate(False)
            ctk.CTkLabel(badge, text=loader.upper(),
                         font=ctk.CTkFont(size=11, weight="bold"),
                         fg_color=color, corner_radius=6,
                         text_color="white", width=82, height=28).pack()
            ctk.CTkLabel(badge, text=f"MC {ver}",
                         font=ctk.CTkFont(size=9), text_color="#888").pack(pady=(3, 0))

            # Info
            ctk.CTkLabel(card, text=inst.get("name", "Instalacja"),
                         font=ctk.CTkFont(size=16, weight="bold"),
                         anchor="w").grid(row=0, column=1, sticky="w", pady=(12, 0))
            ctk.CTkLabel(card,
                         text=f"Czas gry: {stats['total_time']}  •  "
                              f"Sesji: {stats['sessions']}  •  "
                              f"Ostatnio: {stats['last_played']}",
                         font=ctk.CTkFont(size=10), text_color="#666",
                         anchor="w").grid(row=1, column=1, sticky="w")
            status_txt = "✓ zainstalowane" if installed else "⬇ do pobrania"
            status_col = "#4CAF50" if installed else "#FF8C00"
            ctk.CTkLabel(card, text=status_txt,
                         font=ctk.CTkFont(size=10), text_color=status_col,
                         anchor="w").grid(row=2, column=1, sticky="w", pady=(0, 12))

            # PLAY button
            play_text = "▶  GRAJ" if installed else "⬇  Zainstaluj"
            play_color = "#4CAF50" if installed else "#2196F3"
            ctk.CTkButton(card, text=play_text, width=120, height=44,
                          fg_color=play_color, hover_color="#388E3C" if installed else "#1565C0",
                          font=ctk.CTkFont(size=14, weight="bold"),
                          command=self._on_play or (lambda: None)).grid(
                row=0, column=2, rowspan=3, padx=16, pady=12)
        else:
            ctk.CTkLabel(card,
                         text="Wybierz instalację na stronie głównej lub utwórz nową.",
                         font=ctk.CTkFont(size=13), text_color="#666").grid(
                row=0, column=0, padx=20, pady=20)
            ctk.CTkButton(card, text="＋ Nowa instalacja", height=34,
                          fg_color="#FF6B35", hover_color="#e05520",
                          command=lambda: self._navigate("wizard")).grid(
                row=0, column=1, padx=12, pady=16)

        return row + 1

    # ── sekcja: szybkie statystyki ────────────────────────────────────────────

    def _section_stats(self, row: int) -> int:
        installations = load_installations()
        meta   = load_meta()
        n_mods = len(meta)
        n_inst = len(installations)
        sessions = get_recent_sessions(100)
        total_h  = sum(s.get("duration_s", 0) for s in sessions) // 3600

        stats = [
            ("🎮", f"{n_inst}", "instalacje"),
            ("📦", f"{n_mods}", "mody"),
            ("⏱", f"{total_h}h", "łącznie"),
            ("🎯", f"{len(sessions)}", "sesji"),
        ]

        frame = ctk.CTkFrame(self._scroll, fg_color="transparent")
        frame.grid(row=row, column=0, sticky="ew", pady=(0, 10))
        for i, (icon, val, label) in enumerate(stats):
            c = ctk.CTkFrame(frame, corner_radius=10)
            c.pack(side="left", expand=True, fill="x", padx=(0 if i==0 else 5, 0))
            ctk.CTkLabel(c, text=icon, font=ctk.CTkFont(size=22)).pack(pady=(10, 0))
            ctk.CTkLabel(c, text=val,
                         font=ctk.CTkFont(size=18, weight="bold"),
                         text_color="#FF6B35").pack()
            ctk.CTkLabel(c, text=label,
                         font=ctk.CTkFont(size=10), text_color="#666").pack(pady=(0, 10))

        return row + 1

    # ── sekcja: serwery ───────────────────────────────────────────────────────

    def _section_servers(self, row: int) -> int:
        servers = get_servers()
        if not servers:
            return row

        header = ctk.CTkFrame(self._scroll, fg_color="transparent")
        header.grid(row=row, column=0, sticky="ew", pady=(4, 4))
        ctk.CTkLabel(header, text="🖥  ULUBIONE SERWERY",
                     font=ctk.CTkFont(size=9, weight="bold"),
                     text_color="#555").pack(side="left")
        ctk.CTkButton(header, text="Wszystkie serwery", height=22, width=120,
                      fg_color="transparent", hover_color="#2a2a2a",
                      text_color="#666", font=ctk.CTkFont(size=10),
                      command=lambda: self._navigate("server_browser")).pack(side="right")

        srv_frame = ctk.CTkFrame(self._scroll, corner_radius=10)
        srv_frame.grid(row=row + 1, column=0, sticky="ew", pady=(0, 10))
        srv_frame.columnconfigure(0, weight=1)

        self._srv_labels: dict[int, ctk.CTkLabel] = {}
        for i, srv in enumerate(servers[:4]):
            self._make_server_row(srv_frame, i, srv)

        # Pinguj w tle
        def _cb(idx: int, status: ServerStatus):
            self._server_status[idx] = status
            self.after(0, lambda i=idx, s=status: self._update_server_label(i, s))
        ping_all_async(_cb)

        return row + 2

    def _make_server_row(self, parent, idx: int, srv: dict):
        row = ctk.CTkFrame(parent, fg_color="transparent", height=44)
        row.grid(row=idx, column=0, sticky="ew", padx=12, pady=2)
        row.columnconfigure(1, weight=1)
        row.grid_propagate(False)

        # Status dot (placeholder)
        self._srv_labels[idx] = ctk.CTkLabel(
            row, text="⏳", font=ctk.CTkFont(size=12), width=20)
        self._srv_labels[idx].grid(row=0, column=0, padx=(0, 8), pady=8)

        ctk.CTkLabel(row, text=srv.get("name", srv.get("address", "?")),
                     font=ctk.CTkFont(size=12, weight="bold"),
                     anchor="w").grid(row=0, column=1, sticky="w")

        ctk.CTkLabel(row, text=srv.get("address", ""),
                     font=ctk.CTkFont(size=9), text_color="#555",
                     anchor="w").grid(row=0, column=2, padx=(8, 0))

        ctk.CTkButton(row, text="Dołącz", width=64, height=26,
                      fg_color="#FF6B35", hover_color="#e05520",
                      font=ctk.CTkFont(size=10),
                      command=lambda s=srv: self._navigate(
                          "server_browser", server=s)).grid(
            row=0, column=3, padx=(8, 0))

    def _update_server_label(self, idx: int, status: ServerStatus):
        lbl = self._srv_labels.get(idx)
        if not lbl:
            return
        try:
            if not lbl.winfo_exists():
                return
            if status.online:
                lbl.configure(
                    text=f"🟢",
                    text_color="#4CAF50")
            else:
                lbl.configure(text="🔴", text_color="#FF4444")
        except Exception:
            pass

    # ── sekcja: ostatnie sesje ────────────────────────────────────────────────

    def _section_recent_sessions(self, row: int) -> int:
        sessions = get_recent_sessions(3)
        if not sessions:
            return row

        ctk.CTkLabel(self._scroll, text="🕓  OSTATNIE SESJE",
                     font=ctk.CTkFont(size=9, weight="bold"),
                     text_color="#555").grid(
            row=row, column=0, sticky="w", pady=(4, 4))

        card = ctk.CTkFrame(self._scroll, corner_radius=10)
        card.grid(row=row + 1, column=0, sticky="ew", pady=(0, 10))

        for i, s in enumerate(sessions):
            dur  = self._fmt_dur(s.get("duration_s", 0))
            fps  = s.get("avg_fps", 0)
            cpu  = s.get("avg_cpu", 0)
            date = s.get("start", "")[:10]
            inst = s.get("installation", "")

            r = ctk.CTkFrame(card, fg_color="transparent")
            r.pack(fill="x", padx=12, pady=4)

            ctk.CTkLabel(r, text=f"🎮 {inst[:20]}",
                         font=ctk.CTkFont(size=11, weight="bold"),
                         anchor="w", width=160).pack(side="left")
            ctk.CTkLabel(r, text=f"{date}  •  {dur}",
                         font=ctk.CTkFont(size=10), text_color="#666").pack(side="left", padx=8)
            if fps > 0:
                ctk.CTkLabel(r, text=f"FPS: {fps:.0f}",
                             font=ctk.CTkFont(size=10), text_color="#4CAF50").pack(side="left", padx=4)
            ctk.CTkLabel(r, text=f"CPU: {cpu:.0f}%",
                         font=ctk.CTkFont(size=10), text_color="#888").pack(side="left", padx=4)

        return row + 2

    # ── sekcja: aktualności ───────────────────────────────────────────────────

    def _section_news(self, row: int) -> int:
        ctk.CTkLabel(self._scroll, text="📰  AKTUALNOŚCI",
                     font=ctk.CTkFont(size=9, weight="bold"),
                     text_color="#555").grid(
            row=row, column=0, sticky="w", pady=(4, 4))

        news_items = [
            ("Moddy 2.0",    "Nowy launcher z AI generatorem paczek!",   "#FF6B35"),
            ("Fabric 0.16",  "Nowa wersja loaderów dla MC 1.21.x",       "#7EB5D6"),
            ("Modrinth",     "Ponad 50 000 modów w repozytorium",        "#1BD96A"),
        ]
        card = ctk.CTkFrame(self._scroll, corner_radius=10)
        card.grid(row=row + 1, column=0, sticky="ew", pady=(0, 10))

        for icon_color, title, desc in news_items:
            r = ctk.CTkFrame(card, fg_color="transparent")
            r.pack(fill="x", padx=12, pady=5)
            ctk.CTkLabel(r, text="●", text_color=desc,
                         font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 8))
            ctk.CTkLabel(r, text=f"{icon_color}  {title}",
                         font=ctk.CTkFont(size=11, weight="bold"),
                         anchor="w").pack(side="left")

        return row + 2

    # ── helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _fmt_dur(secs: int) -> str:
        if secs < 60:    return f"{secs}s"
        if secs < 3600:  return f"{secs // 60}m"
        return f"{secs // 3600}h {(secs % 3600) // 60}m"

    @staticmethod
    def _is_installed(inst: dict) -> bool:
        try:
            from ...core.minecraft_launcher import is_installed
            return is_installed(inst)
        except Exception:
            return False
