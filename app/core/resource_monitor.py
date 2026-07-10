"""
Monitorowanie RAM i CPU podczas gry.
Używa psutil do odczytu zasobów systemowych.
"""
from __future__ import annotations
import threading
import time
from dataclasses import dataclass, field
from collections import deque
from typing import Callable

try:
    import psutil
    _HAS_PSUTIL = True
except ImportError:
    _HAS_PSUTIL = False


@dataclass
class ResourceSnapshot:
    cpu_percent:   float = 0.0
    ram_used_mb:   float = 0.0
    ram_total_mb:  float = 0.0
    ram_percent:   float = 0.0
    # Ostatnie N pomiarów (dla wykresu)
    cpu_history:   list[float] = field(default_factory=list)
    ram_history:   list[float] = field(default_factory=list)

    @property
    def ram_free_mb(self) -> float:
        return self.ram_total_mb - self.ram_used_mb

    def ram_label(self) -> str:
        return f"{self.ram_used_mb:.0f} / {self.ram_total_mb:.0f} MB"

    def cpu_label(self) -> str:
        return f"{self.cpu_percent:.1f}%"


class ResourceMonitor:
    """Monitoruje zasoby w tle i wywołuje callback co `interval` sekund."""

    HISTORY_LEN = 60   # ostatnie 60 próbek

    def __init__(self, interval: float = 2.0):
        self._interval  = interval
        self._running   = False
        self._callback: Callable[[ResourceSnapshot], None] | None = None
        self._snapshot  = ResourceSnapshot()
        self._cpu_hist: deque[float] = deque(maxlen=self.HISTORY_LEN)
        self._ram_hist: deque[float] = deque(maxlen=self.HISTORY_LEN)

    def set_callback(self, fn: Callable[[ResourceSnapshot], None]):
        self._callback = fn

    def start(self):
        if not _HAS_PSUTIL or self._running:
            return
        self._running = True
        threading.Thread(target=self._loop, daemon=True).start()

    def stop(self):
        self._running = False

    @property
    def snapshot(self) -> ResourceSnapshot:
        return self._snapshot

    @property
    def available(self) -> bool:
        return _HAS_PSUTIL

    def _loop(self):
        # Pierwsze wywołanie bez blokowania (interval=0.1)
        psutil.cpu_percent(interval=None)
        while self._running:
            try:
                cpu = psutil.cpu_percent(interval=None)
                mem = psutil.virtual_memory()

                self._cpu_hist.append(cpu)
                self._ram_hist.append(mem.used / 1024 / 1024)

                self._snapshot = ResourceSnapshot(
                    cpu_percent  = cpu,
                    ram_used_mb  = mem.used  / 1024 / 1024,
                    ram_total_mb = mem.total / 1024 / 1024,
                    ram_percent  = mem.percent,
                    cpu_history  = list(self._cpu_hist),
                    ram_history  = list(self._ram_hist),
                )
                if self._callback:
                    self._callback(self._snapshot)
            except Exception:
                pass
            time.sleep(self._interval)

    def get_alert(self, ram_warn_pct: float = 85.0,
                  cpu_warn_pct: float = 95.0) -> str | None:
        """Zwraca komunikat alertu jeśli zasoby są na wyczerpaniu."""
        s = self._snapshot
        if s.ram_percent >= ram_warn_pct:
            return f"⚠ RAM {s.ram_percent:.0f}% ({s.ram_used_mb:.0f} MB)"
        if s.cpu_percent >= cpu_warn_pct:
            return f"⚠ CPU {s.cpu_percent:.1f}%"
        return None
