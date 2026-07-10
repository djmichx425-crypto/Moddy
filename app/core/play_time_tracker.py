"""
Śledzenie czasu gry i statystyk sesji.
"""
from __future__ import annotations
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

APPDATA    = Path(os.environ.get("APPDATA", "~"))
STATS_FILE = APPDATA / "moddy" / "play_stats.json"


def _load() -> dict:
    if STATS_FILE.exists():
        try:
            return json.loads(STATS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"sessions": [], "total_seconds": 0}


def _save(data: dict):
    STATS_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def start_session(installation_name: str) -> str:
    """Rejestruje start sesji. Zwraca session_id."""
    sid = datetime.now().strftime("%Y%m%d_%H%M%S")
    data = _load()
    data["sessions"].append({
        "id":           sid,
        "installation": installation_name,
        "start":        datetime.now().isoformat(),
        "end":          None,
        "duration_s":   0,
        "avg_cpu":      0.0,
        "avg_ram_mb":   0.0,
        "avg_fps":      0.0,
        "cpu_samples":  [],
        "ram_samples":  [],
    })
    _save(data)
    return sid


def end_session(sid: str, cpu_samples: list[float], ram_samples: list[float],
                fps_samples: list[float]):
    """Zamknij sesję i oblicz średnie."""
    data  = _load()
    for sess in data["sessions"]:
        if sess["id"] == sid:
            now       = datetime.now()
            start     = datetime.fromisoformat(sess["start"])
            duration  = int((now - start).total_seconds())
            sess["end"]        = now.isoformat()
            sess["duration_s"] = duration
            sess["avg_cpu"]    = round(sum(cpu_samples) / max(len(cpu_samples), 1), 1)
            sess["avg_ram_mb"] = round(sum(ram_samples) / max(len(ram_samples), 1), 1)
            sess["avg_fps"]    = round(sum(fps_samples) / max(len(fps_samples), 1), 1)
            sess["cpu_samples"]= cpu_samples[-60:]
            sess["ram_samples"]= ram_samples[-60:]
            data["total_seconds"] = data.get("total_seconds", 0) + duration
            break
    _save(data)


def get_total_playtime() -> str:
    """Zwraca łączny czas gry jako 'Xh Ym'."""
    secs = _load().get("total_seconds", 0)
    return _fmt_duration(secs)


def get_recent_sessions(n: int = 10) -> list[dict]:
    """Ostatnie n sesji, od najnowszej."""
    sessions = [s for s in _load()["sessions"] if s.get("end")]
    return sorted(sessions, key=lambda s: s["start"], reverse=True)[:n]


def get_last_session() -> dict | None:
    sessions = get_recent_sessions(1)
    return sessions[0] if sessions else None


def get_installation_stats(name: str) -> dict:
    sessions = [s for s in _load()["sessions"]
                if s.get("installation") == name and s.get("end")]
    total = sum(s.get("duration_s", 0) for s in sessions)
    return {
        "sessions":    len(sessions),
        "total_time":  _fmt_duration(total),
        "total_secs":  total,
        "last_played": sessions[-1]["start"][:10] if sessions else "–",
    }


def _fmt_duration(secs: int) -> str:
    if secs < 60:
        return f"{secs}s"
    if secs < 3600:
        return f"{secs // 60}m"
    h = secs // 3600
    m = (secs % 3600) // 60
    return f"{h}h {m}m"
