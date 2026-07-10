"""
Zbieranie statystyk wydajności podczas sesji gry.
FPS odczytywany z logów gry. CPU/RAM z psutil.
GPU/Temp przez WMI (Windows) lub GPUtil.
"""
from __future__ import annotations
import re
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Callable

try:
    import psutil
    _HAS_PSUTIL = True
except ImportError:
    _HAS_PSUTIL = False

try:
    import GPUtil
    _HAS_GPUTIL = True
except ImportError:
    _HAS_GPUTIL = False


@dataclass
class FrameStats:
    fps:        float = 0.0
    cpu:        float = 0.0
    ram_mb:     float = 0.0
    gpu_usage:  float = 0.0
    gpu_temp:   float = 0.0
    gpu_name:   str   = ""
    cpu_temp:   float = 0.0
    timestamp:  float = field(default_factory=time.time)


class SessionStatsCollector:
    """Zbiera statystyki w tle podczas gry."""

    HISTORY = 300   # 5 minut przy 1Hz

    def __init__(self):
        self._running  = False
        self._fps_hist:  deque[float] = deque(maxlen=self.HISTORY)
        self._cpu_hist:  deque[float] = deque(maxlen=self.HISTORY)
        self._ram_hist:  deque[float] = deque(maxlen=self.HISTORY)
        self._gpu_hist:  deque[float] = deque(maxlen=self.HISTORY)
        self._temp_hist: deque[float] = deque(maxlen=self.HISTORY)
        self._current   = FrameStats()
        self._callback: Callable[[FrameStats], None] | None = None
        self._log_path: str | None = None

    def set_callback(self, fn: Callable[[FrameStats], None]):
        self._callback = fn

    def set_log_path(self, path: str):
        self._log_path = path

    def start(self):
        self._running = True
        threading.Thread(target=self._loop, daemon=True).start()

    def stop(self):
        self._running = False

    def get_history(self) -> dict:
        return {
            "fps":  list(self._fps_hist),
            "cpu":  list(self._cpu_hist),
            "ram":  list(self._ram_hist),
            "gpu":  list(self._gpu_hist),
            "temp": list(self._temp_hist),
        }

    def get_current(self) -> FrameStats:
        return self._current

    def get_session_averages(self) -> dict:
        def avg(d):
            return round(sum(d) / max(len(d), 1), 1) if d else 0.0
        return {
            "avg_fps":  avg(self._fps_hist),
            "avg_cpu":  avg(self._cpu_hist),
            "avg_ram":  avg(self._ram_hist),
            "avg_gpu":  avg(self._gpu_hist),
            "peak_fps": max(self._fps_hist, default=0.0),
            "peak_ram": max(self._ram_hist, default=0.0),
        }

    # ── loop ──────────────────────────────────────────────────────────────────

    def _loop(self):
        if _HAS_PSUTIL:
            psutil.cpu_percent(interval=None)   # init

        while self._running:
            s = FrameStats()

            # CPU / RAM
            if _HAS_PSUTIL:
                s.cpu    = psutil.cpu_percent(interval=None)
                mem      = psutil.virtual_memory()
                s.ram_mb = mem.used / 1024 / 1024

            # GPU
            if _HAS_GPUTIL:
                try:
                    gpus = GPUtil.getGPUs()
                    if gpus:
                        g = gpus[0]
                        s.gpu_usage = g.load * 100
                        s.gpu_temp  = g.temperature
                        s.gpu_name  = g.name
                except Exception:
                    pass

            # FPS z logów
            if self._log_path:
                s.fps = self._read_fps_from_log()

            self._fps_hist.append(s.fps)
            self._cpu_hist.append(s.cpu)
            self._ram_hist.append(s.ram_mb)
            self._gpu_hist.append(s.gpu_usage)
            self._temp_hist.append(s.gpu_temp)
            self._current = s

            if self._callback:
                self._callback(s)

            time.sleep(1.0)

    def _read_fps_from_log(self) -> float:
        """Szuka FPS w ostatnich liniach logu Minecraft."""
        try:
            with open(self._log_path, "rb") as f:
                f.seek(max(0, f.seek(0, 2) - 4096))
                tail = f.read().decode("utf-8", errors="ignore")
            # "fps: 120" lub "120 fps" lub "FPS: 120"
            matches = re.findall(r'(\d+)\s*fps|fps[:\s]+(\d+)', tail, re.IGNORECASE)
            if matches:
                for m in reversed(matches):
                    val = m[0] or m[1]
                    if val:
                        return float(val)
        except Exception:
            pass
        return 0.0
