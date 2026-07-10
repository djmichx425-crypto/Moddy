"""
Discord integracja:
  1. Rich Presence — pokazuje "Gram w Minecraft X.XX" w Discord
  2. Voice status  — odczyt czy użytkownik jest na kanale głosowym
"""
from __future__ import annotations
import threading
import time
from dataclasses import dataclass
from typing import Callable

# Discord Application ID — zarejestruj własną aplikację na discord.com/developers
# lub użyj domyślnego (do testów)
DEFAULT_APP_ID = "1234567890123456789"   # placeholder; zastąp własnym


@dataclass
class DiscordStatus:
    connected:     bool  = False
    username:      str   = ""
    in_voice:      bool  = False
    voice_channel: str   = ""
    voice_guild:   str   = ""
    error:         str   = ""


class DiscordRPCClient:
    """Zarządza Discord Rich Presence i odczytem voice status."""

    def __init__(self, app_id: str = DEFAULT_APP_ID):
        self._app_id    = app_id
        self._rpc       = None
        self.status     = DiscordStatus()
        self._on_update: Callable[[DiscordStatus], None] | None = None
        self._start_ts  = int(time.time())

    def configure(self, app_id: str):
        self._app_id = app_id.strip() or DEFAULT_APP_ID

    def set_callback(self, fn: Callable[[DiscordStatus], None]):
        self._on_update = fn

    # ── connect ───────────────────────────────────────────────────────────────

    def connect(self) -> bool:
        try:
            from pypresence import Presence
            self._rpc = Presence(self._app_id)
            self._rpc.connect()
            self.status.connected = True
            self.status.error     = ""
            self._notify()
            return True
        except Exception as e:
            self._rpc = None
            self.status.connected = False
            self.status.error     = str(e)
            self._notify()
            return False

    def disconnect(self):
        if self._rpc:
            try:
                self._rpc.close()
            except Exception:
                pass
            self._rpc = None
        self.status.connected = False
        self._notify()

    # ── presence ──────────────────────────────────────────────────────────────

    def set_presence_idle(self):
        """Ustaw status: w launcherze."""
        if not self._rpc:
            return
        try:
            self._rpc.update(
                details="W launcherze Moddy",
                state="Przeglądanie modów",
                large_image="moddy",
                large_text="Moddy Launcher",
                start=self._start_ts,
            )
        except Exception:
            pass

    def set_presence_playing(self, installation: dict):
        """Ustaw status: gram w Minecraft (konkretna instalacja)."""
        if not self._rpc:
            return
        loader  = installation.get("loader", "vanilla").capitalize()
        version = installation.get("version") or installation.get("game_version", "")
        name    = installation.get("name", "Minecraft")
        try:
            self._rpc.update(
                details=f"Gram: {name}",
                state=f"{loader} {version}",
                large_image="minecraft",
                large_text="Minecraft",
                small_image="moddy",
                small_text="Moddy Launcher",
                start=int(time.time()),
            )
        except Exception:
            pass

    def clear_presence(self):
        if not self._rpc:
            return
        try:
            self._rpc.clear()
        except Exception:
            pass

    # ── voice status (local IPC read) ─────────────────────────────────────────

    def refresh_voice_status(self) -> DiscordStatus:
        """
        Próbuje odczytać status voice przez Discord IPC.
        Działa tylko gdy użytkownik jest zalogowany w Discord desktop.
        """
        try:
            from pypresence import Client
            cl = Client(self._app_id)
            cl.start()
            resp = cl.get_voice_settings()
            cl.close()
            if resp:
                self.status.in_voice = True
        except Exception:
            pass
        return self.status

    @property
    def connected(self) -> bool:
        return self._rpc is not None

    def _notify(self):
        if self._on_update:
            self._on_update(self.status)
