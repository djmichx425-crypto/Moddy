"""
Strona ustawień integracji.
Zakładki: OBS | Spotify | Discord | Oceny
"""
import tkinter as tk
import customtkinter as ctk
import threading

from ...core.mod_library import load_settings, save_settings


class IntegrationsPage(ctk.CTkFrame):

    def __init__(self, parent, navigate,
                 obs=None, spotify=None, discord=None, **kwargs):
        super().__init__(parent, corner_radius=0, fg_color="#1a1a1a", **kwargs)
        self._navigate = navigate
        self._obs      = obs
        self._spotify  = spotify
        self._discord  = discord
        self._build()

    def set_clients(self, obs=None, spotify=None, discord=None):
        """Wywoływane po asynchronicznej inicjalizacji integracji."""
        self._obs     = obs
        self._spotify = spotify
        self._discord = discord

    # ── build ─────────────────────────────────────────────────────────────────

    def _build(self):
        top = ctk.CTkFrame(self, fg_color="#1e1e1e", corner_radius=0)
        top.pack(fill="x")
        ctk.CTkLabel(top, text="Integracje",
                     font=ctk.CTkFont(size=17, weight="bold")).pack(
            side="left", padx=20, pady=13)

        tab = ctk.CTkTabview(self, corner_radius=8)
        tab.pack(fill="both", expand=True, padx=16, pady=12)

        for name in ("🔴  OBS", "🎵  Spotify", "🎮  Discord", "⭐  Oceny"):
            tab.add(name)

        self._build_obs(tab.tab("🔴  OBS"))
        self._build_spotify(tab.tab("🎵  Spotify"))
        self._build_discord(tab.tab("🎮  Discord"))
        self._build_ratings(tab.tab("⭐  Oceny"))

    # ══════════════════════════════════════════════════════════════════════════
    #  OBS
    # ══════════════════════════════════════════════════════════════════════════

    def _build_obs(self, parent):
        card = self._card(parent, "🔴  OBS Studio", row=0)

        ctk.CTkLabel(card,
                     text="Połącz Moddy z OBS przez WebSocket (OBS 28+).\n"
                          "OBS → Narzędzia → WebSocket Server Settings → Enable",
                     font=ctk.CTkFont(size=11), text_color="#888",
                     justify="left").pack(anchor="w", padx=16, pady=(0, 10))

        form = ctk.CTkFrame(card, fg_color="transparent")
        form.pack(fill="x", padx=16)
        form.columnconfigure(1, weight=1)

        labels = ["Host:", "Port:", "Hasło WebSocket:"]
        defaults = ["localhost", "4455", ""]
        self._obs_entries: dict[str, ctk.CTkEntry] = {}
        for i, (lbl, ph) in enumerate(zip(labels, defaults)):
            ctk.CTkLabel(form, text=lbl, anchor="w",
                         font=ctk.CTkFont(size=12)).grid(
                row=i, column=0, sticky="w", pady=5)
            e = ctk.CTkEntry(form, placeholder_text=ph,
                             show="*" if "Hasło" in lbl else "",
                             height=32)
            e.grid(row=i, column=1, sticky="ew", padx=(8, 0), pady=5)
            self._obs_entries[lbl] = e

        self._obs_auto_rec = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(card, text="Auto-start nagrywania przy uruchomieniu gry",
                        variable=self._obs_auto_rec,
                        font=ctk.CTkFont(size=11)).pack(
            anchor="w", padx=16, pady=(8, 4))

        self._obs_auto_stop = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(card, text="Auto-stop nagrywania po zamknięciu gry",
                        variable=self._obs_auto_stop,
                        font=ctk.CTkFont(size=11)).pack(
            anchor="w", padx=16, pady=(0, 4))

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=(8, 14))
        ctk.CTkButton(row, text="Połącz z OBS", width=140, height=34,
                      fg_color="#CC0000", hover_color="#990000",
                      command=self._obs_connect).pack(side="left")
        self._obs_status = ctk.CTkLabel(row, text="⚫ Rozłączony",
                                         font=ctk.CTkFont(size=11),
                                         text_color="#555")
        self._obs_status.pack(side="left", padx=12)

    def _obs_connect(self):
        if not self._obs:
            return
        host = self._obs_entries["Host:"].get().strip() or "localhost"
        port = int(self._obs_entries["Port:"].get().strip() or "4455")
        pwd  = self._obs_entries["Hasło WebSocket:"].get()
        self._obs.disconnect()
        self._obs._host     = host
        self._obs._port     = port
        self._obs._password = pwd

        self._obs_status.configure(text="⏳ Łączenie…", text_color="#888")

        def _connect():
            ok = self._obs.connect()
            def _update():
                if ok:
                    self._obs_status.configure(
                        text="🟢 Połączono", text_color="#4CAF50")
                else:
                    self._obs_status.configure(
                        text=f"🔴 Błąd: {self._obs.status.error}",
                        text_color="#FF4444")
            self.after(0, _update)
        threading.Thread(target=_connect, daemon=True).start()

    # ══════════════════════════════════════════════════════════════════════════
    #  SPOTIFY
    # ══════════════════════════════════════════════════════════════════════════

    def _build_spotify(self, parent):
        card = self._card(parent, "🎵  Spotify", row=0)

        ctk.CTkLabel(card,
                     text="Mini player Spotify. Wymaga konta Spotify i aplikacji w\n"
                          "Spotify Developer Dashboard (developer.spotify.com/dashboard).",
                     font=ctk.CTkFont(size=11), text_color="#888",
                     justify="left").pack(anchor="w", padx=16, pady=(0, 10))

        form = ctk.CTkFrame(card, fg_color="transparent")
        form.pack(fill="x", padx=16)
        form.columnconfigure(1, weight=1)

        ctk.CTkLabel(form, text="Client ID:", anchor="w",
                     font=ctk.CTkFont(size=12)).grid(row=0, column=0, sticky="w", pady=5)
        self._sp_client_id = ctk.CTkEntry(form, placeholder_text="Spotify Client ID", height=32)
        self._sp_client_id.grid(row=0, column=1, sticky="ew", padx=(8, 0), pady=5)

        ctk.CTkLabel(form, text="Client Secret:", anchor="w",
                     font=ctk.CTkFont(size=12)).grid(row=1, column=0, sticky="w", pady=5)
        self._sp_secret = ctk.CTkEntry(form, show="*",
                                        placeholder_text="Spotify Client Secret", height=32)
        self._sp_secret.grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=5)

        ctk.CTkLabel(form,
                     text=f"Redirect URI: http://localhost:8899/callback",
                     font=ctk.CTkFont(size=9), text_color="#555").grid(
            row=2, column=1, sticky="w", padx=(8, 0))

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=(10, 14))
        ctk.CTkButton(row, text="Połącz ze Spotify", width=150, height=34,
                      fg_color="#1DB954", hover_color="#168a3d",
                      command=self._spotify_connect).pack(side="left")
        self._sp_status = ctk.CTkLabel(row, text="⚫ Rozłączony",
                                        font=ctk.CTkFont(size=11), text_color="#555")
        self._sp_status.pack(side="left", padx=12)

    def _spotify_connect(self):
        if not self._spotify:
            return
        cid  = self._sp_client_id.get().strip()
        csec = self._sp_secret.get().strip()
        if not cid or not csec:
            self._sp_status.configure(
                text="⚠ Podaj Client ID i Secret", text_color="#FF8C00")
            return
        self._spotify.configure(cid, csec)
        self._sp_status.configure(text="⏳ Łączenie (przeglądarka)…", text_color="#888")

        s = load_settings()
        s["spotify_client_id"]     = cid
        s["spotify_client_secret"] = csec
        save_settings(s)

        def _conn():
            ok = self._spotify.connect()
            def _upd():
                if ok:
                    self._sp_status.configure(
                        text="🟢 Połączono", text_color="#4CAF50")
                    self._spotify.start_polling()
                else:
                    self._sp_status.configure(
                        text="🔴 Błąd logowania", text_color="#FF4444")
            self.after(0, _upd)
        threading.Thread(target=_conn, daemon=True).start()

    # ══════════════════════════════════════════════════════════════════════════
    #  DISCORD
    # ══════════════════════════════════════════════════════════════════════════

    def _build_discord(self, parent):
        card = self._card(parent, "🎮  Discord Rich Presence", row=0)

        ctk.CTkLabel(card,
                     text="Pokazuje w Discord co grasz (Minecraft + loader + wersja).\n"
                          "Zarejestruj aplikację na discord.com/developers i wklej Application ID.",
                     font=ctk.CTkFont(size=11), text_color="#888",
                     justify="left").pack(anchor="w", padx=16, pady=(0, 10))

        form = ctk.CTkFrame(card, fg_color="transparent")
        form.pack(fill="x", padx=16)
        form.columnconfigure(1, weight=1)

        ctk.CTkLabel(form, text="Application ID:", anchor="w",
                     font=ctk.CTkFont(size=12)).grid(row=0, column=0, sticky="w", pady=5)
        self._disc_app_id = ctk.CTkEntry(form,
                                          placeholder_text="123456789012345678",
                                          height=32)
        self._disc_app_id.grid(row=0, column=1, sticky="ew", padx=(8, 0), pady=5)

        self._disc_auto = tk.BooleanVar(value=True)
        ctk.CTkCheckBox(card, text="Automatycznie aktualizuj status przy uruchomieniu gry",
                        variable=self._disc_auto,
                        font=ctk.CTkFont(size=11)).pack(
            anchor="w", padx=16, pady=(8, 4))

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=(8, 14))
        ctk.CTkButton(row, text="Połącz z Discord", width=150, height=34,
                      fg_color="#5865F2", hover_color="#4752c4",
                      command=self._discord_connect).pack(side="left")
        ctk.CTkButton(row, text="Wyczyść status", width=130, height=34,
                      fg_color="#3a3a3a", hover_color="#555",
                      command=self._discord_clear).pack(side="left", padx=6)
        self._disc_status = ctk.CTkLabel(row, text="⚫ Rozłączony",
                                          font=ctk.CTkFont(size=11), text_color="#555")
        self._disc_status.pack(side="left", padx=8)

    def _discord_connect(self):
        if not self._discord:
            return
        app_id = self._disc_app_id.get().strip()
        if app_id:
            self._discord.configure(app_id)
            s = load_settings()
            s["discord_app_id"] = app_id
            save_settings(s)

        self._disc_status.configure(text="⏳ Łączenie…", text_color="#888")

        def _conn():
            ok = self._discord.connect()
            def _upd():
                if ok:
                    self._disc_status.configure(
                        text="🟢 Połączono", text_color="#4CAF50")
                    self._discord.set_presence_idle()
                else:
                    self._disc_status.configure(
                        text=f"🔴 {self._discord.status.error or 'Błąd'}",
                        text_color="#FF4444")
            self.after(0, _upd)
        threading.Thread(target=_conn, daemon=True).start()

    def _discord_clear(self):
        if self._discord:
            self._discord.clear_presence()
            self._disc_status.configure(text="⚫ Status wyczyszczony",
                                         text_color="#555")

    # ══════════════════════════════════════════════════════════════════════════
    #  RATINGS
    # ══════════════════════════════════════════════════════════════════════════

    def _build_ratings(self, parent):
        from ...core.ratings_manager import all_ratings, delete_rating

        card = self._card(parent, "⭐  Twoje oceny modów", row=0)

        self._ratings_scroll = ctk.CTkScrollableFrame(card, height=340)
        self._ratings_scroll.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self._ratings_scroll.columnconfigure(0, weight=1)

        self._refresh_ratings_list()

    def _refresh_ratings_list(self):
        from ...core.ratings_manager import all_ratings, delete_rating
        for w in self._ratings_scroll.winfo_children():
            w.destroy()

        data = all_ratings()
        if not data:
            ctk.CTkLabel(self._ratings_scroll,
                         text="Nie oceniłeś jeszcze żadnego moda.\n"
                              "Kliknij ⭐ na karcie moda aby wystawić ocenę.",
                         font=ctk.CTkFont(size=12), text_color="#555",
                         justify="center").grid(row=0, column=0, pady=40)
            return

        for i, (key, entry) in enumerate(sorted(data.items())):
            source, mod_id = key.split(":", 1) if ":" in key else ("?", key)
            stars   = entry.get("stars", 0)
            name    = entry.get("mod_name", mod_id)
            comment = entry.get("comment", "")
            date    = entry.get("date", "")

            row = ctk.CTkFrame(self._ratings_scroll, corner_radius=8)
            row.grid(row=i, column=0, sticky="ew", pady=3)
            row.columnconfigure(1, weight=1)

            ctk.CTkLabel(row, text="⭐" * stars + "☆" * (5 - stars),
                         font=ctk.CTkFont(size=13),
                         text_color="#FFD700").grid(
                row=0, column=0, padx=10, pady=(8, 0))
            ctk.CTkLabel(row, text=name,
                         font=ctk.CTkFont(size=12, weight="bold"),
                         anchor="w").grid(row=0, column=1, sticky="w")
            ctk.CTkLabel(row,
                         text=(f"{comment[:60]}…" if len(comment) > 60 else comment)
                              + f"  [{source}]  {date}",
                         font=ctk.CTkFont(size=10), text_color="#666",
                         anchor="w").grid(row=1, column=1, sticky="w", pady=(0, 8))

            ctk.CTkButton(row, text="✕", width=26, height=26,
                          fg_color="#2a2a2a", hover_color="#aa2222",
                          command=lambda k=key, s=source, m=mod_id: (
                              delete_rating(s, m),
                              self._refresh_ratings_list()
                          )).grid(row=0, column=2, padx=8)

    # ── on_show ───────────────────────────────────────────────────────────────

    def on_show(self, **_):
        s = load_settings()
        # Wypełnij zapisane wartości
        if s.get("spotify_client_id"):
            self._sp_client_id.delete(0, "end")
            self._sp_client_id.insert(0, s["spotify_client_id"])
        if s.get("discord_app_id"):
            self._disc_app_id.delete(0, "end")
            self._disc_app_id.insert(0, s["discord_app_id"])
        self._refresh_ratings_list()

    # ── helper ────────────────────────────────────────────────────────────────

    def _card(self, parent, title: str, row: int) -> ctk.CTkFrame:
        card = ctk.CTkFrame(parent, corner_radius=12)
        card.pack(fill="both", expand=True, padx=4, pady=4)
        ctk.CTkLabel(card, text=title,
                     font=ctk.CTkFont(size=14, weight="bold")).pack(
            anchor="w", padx=16, pady=(14, 8))
        return card
