"""
Przeglądarka serwerów + One-Click Join.
"""
import tkinter as tk
import customtkinter as ctk
import threading

from ...core.server_manager import (
    get_servers, add_server, remove_server, toggle_favorite,
    ping_server, ping_all_async, prepare_join, ServerStatus,
)
from ...core.minecraft_launcher import is_installed, launch
from ...core.accounts_manager import get_selected_account


class ServerBrowserPage(ctk.CTkFrame):

    def __init__(self, parent, navigate,
                 get_selected_inst=None,
                 on_launch=None,
                 **kwargs):
        super().__init__(parent, corner_radius=0, fg_color="#1a1a1a", **kwargs)
        self._navigate   = navigate
        self._get_inst   = get_selected_inst
        self._on_launch  = on_launch
        self._status_map: dict[int, ServerStatus] = {}
        self._join_target: dict | None = None
        self._build()

    # ── build ─────────────────────────────────────────────────────────────────

    def _build(self):
        top = ctk.CTkFrame(self, fg_color="#1e1e1e", corner_radius=0)
        top.pack(fill="x")
        ctk.CTkLabel(top, text="🖥  Serwery",
                     font=ctk.CTkFont(size=17, weight="bold")).pack(
            side="left", padx=20, pady=13)
        ctk.CTkButton(top, text="⟳ Odśwież", height=30, width=90,
                      fg_color="#2a2a2a", hover_color="#555",
                      command=self._refresh_status).pack(side="right", padx=8, pady=12)

        # Formularz dodawania
        add_card = ctk.CTkFrame(self, corner_radius=10)
        add_card.pack(fill="x", padx=16, pady=(8, 4))
        row = ctk.CTkFrame(add_card, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=10)

        self._name_e = ctk.CTkEntry(row, placeholder_text="Nazwa serwera", width=150, height=32)
        self._name_e.pack(side="left", padx=(0, 6))
        self._addr_e = ctk.CTkEntry(row, placeholder_text="adres:port", width=180, height=32)
        self._addr_e.pack(side="left", padx=(0, 6))
        ctk.CTkButton(row, text="+ Dodaj", width=80, height=32,
                      fg_color="#4CAF50", hover_color="#388E3C",
                      command=self._add_server).pack(side="left")
        self._add_msg = ctk.CTkLabel(row, text="",
                                      font=ctk.CTkFont(size=10), text_color="#4CAF50")
        self._add_msg.pack(side="left", padx=8)

        # Lista serwerów
        self._scroll = ctk.CTkScrollableFrame(
            self, corner_radius=0, fg_color="transparent")
        self._scroll.pack(fill="both", expand=True, padx=16, pady=4)
        self._scroll.columnconfigure(0, weight=1)

        # Overlay dołączania
        self._join_overlay: ctk.CTkFrame | None = None

    # ── on_show ───────────────────────────────────────────────────────────────

    def on_show(self, server: dict | None = None, **_):
        self._refresh_list()
        self._refresh_status()
        if server:
            self._join_server(server)

    def _refresh_list(self):
        for w in self._scroll.winfo_children():
            w.destroy()

        servers = get_servers()
        if not servers:
            ctk.CTkLabel(self._scroll,
                         text="Brak serwerów.\nDodaj serwer powyżej.",
                         font=ctk.CTkFont(size=13), text_color="#555",
                         justify="center").pack(pady=40)
            return

        for i, srv in enumerate(servers):
            self._make_server_card(i, srv)

    def _make_server_card(self, idx: int, srv: dict):
        card = ctk.CTkFrame(self._scroll, corner_radius=10, height=80)
        card.pack(fill="x", pady=4)
        card.columnconfigure(2, weight=1)
        card.pack_propagate(False)

        # Status indicator
        st = self._status_map.get(idx)
        if st:
            dot = "🟢" if st.online else "🔴"
            tip = f"{st.players}/{st.max_players} graczy" if st.online else st.error[:30]
        else:
            dot, tip = "⏳", "Sprawdzanie…"

        self._dot_labels = getattr(self, "_dot_labels", {})
        dot_lbl = ctk.CTkLabel(card, text=dot, font=ctk.CTkFont(size=16), width=30)
        dot_lbl.grid(row=0, column=0, padx=(10, 4), pady=8, rowspan=2)
        self._dot_labels[idx] = dot_lbl

        ctk.CTkLabel(card, text=srv.get("name", srv.get("address", "?")),
                     font=ctk.CTkFont(size=13, weight="bold"),
                     anchor="w").grid(row=0, column=1, sticky="w", pady=(10, 0))
        ctk.CTkLabel(card, text=f"{srv.get('address', '')}:{srv.get('port', 25565)}",
                     font=ctk.CTkFont(size=9), text_color="#555",
                     anchor="w").grid(row=1, column=1, sticky="w", pady=(0, 8))

        ctk.CTkLabel(card, text=tip,
                     font=ctk.CTkFont(size=10), text_color="#888").grid(
            row=0, column=2, sticky="w", padx=8)

        # Przyciski
        btns = ctk.CTkFrame(card, fg_color="transparent")
        btns.grid(row=0, column=3, rowspan=2, padx=10)

        ctk.CTkButton(btns, text="▶ Dołącz", width=88, height=30,
                      fg_color="#4CAF50", hover_color="#388E3C",
                      font=ctk.CTkFont(size=11, weight="bold"),
                      command=lambda s=srv: self._join_server(s)).pack(pady=(4, 3))

        sub = ctk.CTkFrame(btns, fg_color="transparent")
        sub.pack()
        fav = "★" if srv.get("favorite") else "☆"
        ctk.CTkButton(sub, text=fav, width=30, height=24,
                      fg_color="#2a2a2a", hover_color="#555",
                      text_color="#FFD700",
                      command=lambda i=idx: self._toggle_fav(i)).pack(side="left", padx=(0, 2))
        ctk.CTkButton(sub, text="✕", width=30, height=24,
                      fg_color="#2a2a2a", hover_color="#aa2222",
                      command=lambda i=idx: self._remove_server(i)).pack(side="left")

    # ── One-Click Join ────────────────────────────────────────────────────────

    def _join_server(self, srv: dict):
        inst = self._get_inst() if self._get_inst else None
        if not inst:
            self._navigate("home")
            return

        account = get_selected_account()
        if not account:
            self._navigate("accounts")
            return

        self._show_join_overlay(srv, inst, account)

    def _show_join_overlay(self, srv: dict, inst: dict, account: dict):
        if self._join_overlay and self._join_overlay.winfo_exists():
            self._join_overlay.destroy()

        ov = ctk.CTkFrame(self, corner_radius=0, fg_color="#1a1a1a")
        ov.place(relx=0, rely=0, relwidth=1, relheight=1)
        self._join_overlay = ov

        box = ctk.CTkFrame(ov, corner_radius=16, width=480)
        box.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(box, text="▶  One-Click Join",
                     font=ctk.CTkFont(size=20, weight="bold")).pack(pady=(24, 4))
        ctk.CTkLabel(box, text=srv.get("name", srv.get("address", "?")),
                     font=ctk.CTkFont(size=15), text_color="#FF6B35").pack()
        ctk.CTkLabel(box, text=f"Jako: {account['username']}  •  {inst.get('name', '')}",
                     font=ctk.CTkFont(size=11), text_color="#666").pack(pady=(4, 16))

        self._join_status = ctk.CTkLabel(
            box, text="Przygotowywanie…",
            font=ctk.CTkFont(size=12), text_color="#aaa")
        self._join_status.pack(padx=40)

        self._join_bar = ctk.CTkProgressBar(box, height=8, corner_radius=4)
        self._join_bar.pack(fill="x", padx=40, pady=(6, 16))
        self._join_bar.configure(mode="indeterminate")
        self._join_bar.start()

        ctk.CTkButton(box, text="Anuluj", height=32, width=100,
                      fg_color="#2a2a2a", hover_color="#aa2222",
                      command=lambda: (ov.destroy(), None)).pack(pady=(0, 20))

        def _run():
            def status(s: str):
                self.after(0, lambda m=s: self._join_status.configure(text=m))

            status("Sprawdzanie wymagań serwera…")
            ok, msg = prepare_join(srv, inst, on_status=status)

            if not ok:
                self.after(0, lambda m=msg: (
                    self._join_status.configure(text=f"❌ {m}", text_color="#FF4444"),
                    self._join_bar.stop(),
                ))
                return

            if not is_installed(inst):
                status("Instalowanie Minecraft…")
                from ...core.minecraft_launcher import install_version
                try:
                    install_version(inst)
                    inst["installed"] = True
                except Exception as e:
                    err = str(e)
                    self.after(0, lambda m=err: (
                        self._join_status.configure(text=f"❌ {m}", text_color="#FF4444"),
                    ))
                    return

            status(f"Uruchamianie gry…")
            self.after(500, lambda: (
                self._join_bar.stop(),
                self._join_status.configure(
                    text="🎮 Gra uruchomiona! Połącz się z serwerem.", text_color="#4CAF50"),
            ))

            try:
                launch(inst, account,
                       on_stop=lambda: self.after(0, ov.destroy))
            except Exception as e:
                err = str(e)
                self.after(0, lambda m=err: self._join_status.configure(
                    text=f"❌ {m}", text_color="#FF4444"))

        threading.Thread(target=_run, daemon=True).start()

    # ── actions ───────────────────────────────────────────────────────────────

    def _add_server(self):
        name = self._name_e.get().strip()
        addr = self._addr_e.get().strip()
        if not addr:
            self._add_msg.configure(text="Podaj adres", text_color="#FF6B35")
            return
        add_server(name or addr, addr)
        self._name_e.delete(0, "end")
        self._addr_e.delete(0, "end")
        self._add_msg.configure(text=f"✓ Dodano: {name or addr}", text_color="#4CAF50")
        self.after(2500, lambda: self._add_msg.configure(text=""))
        self._refresh_list()

    def _remove_server(self, idx: int):
        remove_server(idx)
        self._refresh_list()

    def _toggle_fav(self, idx: int):
        toggle_favorite(idx)
        self._refresh_list()

    def _refresh_status(self):
        def _cb(idx: int, status: ServerStatus):
            self._status_map[idx] = status
            dot = "🟢" if status.online else "🔴"
            lbl = getattr(self, "_dot_labels", {}).get(idx)
            if lbl:
                try:
                    if lbl.winfo_exists():
                        self.after(0, lambda l=lbl, d=dot: l.configure(text=d))
                except Exception:
                    pass
        ping_all_async(_cb)
