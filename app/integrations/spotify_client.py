"""
Spotify Web API client.
Wymaga: Client ID + Client Secret ze Spotify Developer Dashboard.
Scope: user-read-currently-playing user-modify-playback-state user-read-playback-state
"""
from __future__ import annotations
import threading
import time
from dataclasses import dataclass, field
from typing import Callable


@dataclass
class SpotifyTrack:
    title:      str   = ""
    artist:     str   = ""
    album:      str   = ""
    album_art:  str   = ""   # URL do okładki
    duration_ms: int  = 0
    progress_ms: int  = 0
    is_playing: bool  = False
    is_available: bool = False


class SpotifyClient:
    """Mini-klient Spotify (odczyt + podstawowe sterowanie)."""

    REDIRECT_URI = "http://localhost:8899/callback"
    SCOPES       = ("user-read-currently-playing "
                    "user-modify-playback-state "
                    "user-read-playback-state")

    def __init__(self):
        self._sp = None
        self._client_id     = ""
        self._client_secret = ""
        self._track         = SpotifyTrack()
        self._poll_id: str | None = None
        self._on_update: Callable[[SpotifyTrack], None] | None = None
        self._polling       = False

    def configure(self, client_id: str, client_secret: str):
        self._client_id     = client_id.strip()
        self._client_secret = client_secret.strip()

    def set_callback(self, fn: Callable[[SpotifyTrack], None]):
        self._on_update = fn

    @property
    def track(self) -> SpotifyTrack:
        return self._track

    # ── connect ───────────────────────────────────────────────────────────────

    def connect(self) -> bool:
        if not self._client_id or not self._client_secret:
            return False
        try:
            import spotipy
            from spotipy.oauth2 import SpotifyOAuth
            auth = SpotifyOAuth(
                client_id=self._client_id,
                client_secret=self._client_secret,
                redirect_uri=self.REDIRECT_URI,
                scope=self.SCOPES,
                open_browser=True,
            )
            self._sp = spotipy.Spotify(auth_manager=auth)
            # test
            self._sp.current_user()
            return True
        except Exception as e:
            self._sp = None
            return False

    def disconnect(self):
        self._polling = False
        self._sp = None
        self._track = SpotifyTrack()
        if self._on_update:
            self._on_update(self._track)

    # ── polling ───────────────────────────────────────────────────────────────

    def start_polling(self, interval: float = 3.0):
        self._polling = True
        threading.Thread(
            target=self._poll_loop, args=(interval,), daemon=True).start()

    def stop_polling(self):
        self._polling = False

    def _poll_loop(self, interval: float):
        while self._polling and self._sp:
            self._refresh()
            time.sleep(interval)

    def _refresh(self):
        try:
            result = self._sp.currently_playing()
            if result and result.get("item"):
                item   = result["item"]
                artists = ", ".join(a["name"] for a in item.get("artists", []))
                images  = (item.get("album", {}).get("images") or [])
                art     = images[0]["url"] if images else ""
                self._track = SpotifyTrack(
                    title       = item.get("name", ""),
                    artist      = artists,
                    album       = item.get("album", {}).get("name", ""),
                    album_art   = art,
                    duration_ms = item.get("duration_ms", 0),
                    progress_ms = result.get("progress_ms", 0),
                    is_playing  = result.get("is_playing", False),
                    is_available = True,
                )
            else:
                self._track = SpotifyTrack(is_available=True)
        except Exception:
            self._track = SpotifyTrack(is_available=bool(self._sp))
        if self._on_update:
            self._on_update(self._track)

    # ── controls ──────────────────────────────────────────────────────────────

    def play_pause(self):
        if not self._sp:
            return
        try:
            if self._track.is_playing:
                self._sp.pause_playback()
            else:
                self._sp.start_playback()
            self._track.is_playing = not self._track.is_playing
            if self._on_update:
                self._on_update(self._track)
        except Exception:
            pass

    def next_track(self):
        if not self._sp:
            return
        try:
            self._sp.next_track()
            threading.Timer(0.5, self._refresh).start()
        except Exception:
            pass

    def prev_track(self):
        if not self._sp:
            return
        try:
            self._sp.previous_track()
            threading.Timer(0.5, self._refresh).start()
        except Exception:
            pass

    @property
    def connected(self) -> bool:
        return self._sp is not None
