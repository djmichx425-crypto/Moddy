"""
Pasek statusu integracji — zawsze widoczny nad dolnym paskiem.
Pokazuje: aktualny utwór Spotify | status OBS | Discord voice
"""
import customtkinter as ctk


class IntegrationBar(ctk.CTkFrame):

    def __init__(self, parent, **kwargs):
        super().__init__(parent, height=28, corner_radius=0,
                         fg_color="#0d0d0d", **kwargs)
        self.pack_propagate(False)
        self._build()

    def _build(self):
        # Spotify
        self._sp_lbl = ctk.CTkLabel(
            self, text="", font=ctk.CTkFont(size=10), text_color="#1DB954")
        self._sp_lbl.pack(side="left", padx=(12, 0))

        self._sp_prev = ctk.CTkButton(
            self, text="⏮", width=22, height=20, font=ctk.CTkFont(size=10),
            fg_color="transparent", hover_color="#1a1a1a",
            command=self._sp_prev_cb)
        self._sp_prev.pack(side="left", padx=1)
        self._sp_prev.pack_forget()

        self._sp_play = ctk.CTkButton(
            self, text="⏸", width=22, height=20, font=ctk.CTkFont(size=10),
            fg_color="transparent", hover_color="#1a1a1a",
            command=self._sp_play_cb)
        self._sp_play.pack(side="left", padx=1)
        self._sp_play.pack_forget()

        self._sp_next = ctk.CTkButton(
            self, text="⏭", width=22, height=20, font=ctk.CTkFont(size=10),
            fg_color="transparent", hover_color="#1a1a1a",
            command=self._sp_next_cb)
        self._sp_next.pack(side="left", padx=(1, 8))
        self._sp_next.pack_forget()

        # OBS
        self._obs_lbl = ctk.CTkLabel(
            self, text="", font=ctk.CTkFont(size=10), text_color="#CC0000")
        self._obs_lbl.pack(side="left", padx=8)

        # Discord
        self._disc_lbl = ctk.CTkLabel(
            self, text="", font=ctk.CTkFont(size=10), text_color="#5865F2")
        self._disc_lbl.pack(side="left", padx=8)

        # Callbacks (set from outside)
        self._spotify_client = None
        self._obs_client     = None

    # ── update methods ────────────────────────────────────────────────────────

    def set_spotify(self, client):
        self._spotify_client = client
        if client:
            client.set_callback(self._on_spotify_update)

    def set_obs(self, client):
        self._obs_client = client
        if client:
            client.set_callback(self._on_obs_update)

    def update_discord(self, status):
        if not self.winfo_exists():
            return
        if status and status.connected:
            if status.in_voice and status.voice_channel:
                self._disc_lbl.configure(
                    text=f"🎮 {status.voice_channel}")
            else:
                self._disc_lbl.configure(text="🎮 Discord")
        else:
            self._disc_lbl.configure(text="")

    def _on_spotify_update(self, track):
        if not self.winfo_exists():
            return
        def _ui():
            if not self.winfo_exists():
                return
            if track.is_available and (track.title or track.is_playing is not None):
                icon = "▶" if track.is_playing else "⏸"
                title = track.title[:28] + "…" if len(track.title) > 28 else track.title
                self._sp_lbl.configure(
                    text=f"🎵 {icon} {title} – {track.artist}")
                self._sp_prev.pack(side="left", padx=1)
                self._sp_play.configure(text="⏸" if track.is_playing else "▶")
                self._sp_play.pack(side="left", padx=1)
                self._sp_next.pack(side="left", padx=(1, 8))
            else:
                self._sp_lbl.configure(text="")
                self._sp_prev.pack_forget()
                self._sp_play.pack_forget()
                self._sp_next.pack_forget()
        self.after(0, _ui)

    def _on_obs_update(self, status):
        if not self.winfo_exists():
            return
        def _ui():
            if not self.winfo_exists():
                return
            if status.connected:
                if status.recording:
                    t = status.recording_time[:8] or ""
                    self._obs_lbl.configure(
                        text=f"🔴 REC {t}", text_color="#FF4444")
                elif status.streaming:
                    self._obs_lbl.configure(
                        text="📡 LIVE", text_color="#FF4444")
                else:
                    self._obs_lbl.configure(
                        text="⚫ OBS", text_color="#555")
            else:
                self._obs_lbl.configure(text="")
        self.after(0, _ui)

    # ── spotify controls ──────────────────────────────────────────────────────

    def _sp_play_cb(self):
        if self._spotify_client:
            self._spotify_client.play_pause()

    def _sp_prev_cb(self):
        if self._spotify_client:
            self._spotify_client.prev_track()

    def _sp_next_cb(self):
        if self._spotify_client:
            self._spotify_client.next_track()
