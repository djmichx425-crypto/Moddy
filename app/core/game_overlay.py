"""
Game Overlay – wykrywa aktywne okno Minecraft i pokazuje overlay Moddy.
Domyślny hotkey: Insert (konfigurowalny w ustawieniach).
"""
from __future__ import annotations
import ctypes
import threading
from typing import Callable


def _get_foreground_title() -> str:
    try:
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        buf  = ctypes.create_unicode_buffer(256)
        ctypes.windll.user32.GetWindowTextW(hwnd, buf, 256)
        return buf.value
    except Exception:
        return ""


def _minecraft_active() -> bool:
    title = _get_foreground_title().lower()
    return "minecraft" in title


class OverlayHotkeyListener:
    """
    Nasłuchuje globalnego hotkey w tle.
    Wywołuje on_trigger() gdy hotkey zostanie naciśnięty podczas gry w Minecraft.
    """

    def __init__(self, on_trigger: Callable, hotkey: str = "insert"):
        self._on_trigger = on_trigger
        self._hotkey     = hotkey
        self._running    = False
        self._thread: threading.Thread | None = None

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread  = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    def set_hotkey(self, key: str):
        self._hotkey = key

    def _loop(self):
        try:
            from pynput import keyboard as kb

            def on_press(key):
                if not self._running:
                    return False  # zatrzymaj listener
                try:
                    name = key.name if hasattr(key, "name") else str(key)
                    if name.lower() == self._hotkey.lower() and _minecraft_active():
                        self._on_trigger()
                except Exception:
                    pass

            with kb.Listener(on_press=on_press) as listener:
                while self._running:
                    import time
                    time.sleep(0.1)
                listener.stop()
        except ImportError:
            # pynput niezainstalowany – cicha praca
            pass
        except Exception:
            pass
