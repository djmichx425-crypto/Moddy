"""
Zarządzanie ulubionymi serwerami Minecraft.
Sprawdzanie statusu online, One-Click Join.
"""
from __future__ import annotations
import json
import os
import socket
import struct
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

APPDATA      = Path(os.environ.get("APPDATA", "~"))
SERVERS_FILE = APPDATA / "moddy" / "servers.json"


@dataclass
class ServerStatus:
    address:   str
    port:      int  = 25565
    online:    bool = False
    players:   int  = 0
    max_players: int = 0
    motd:      str  = ""
    version:   str  = ""
    latency_ms: int = 0
    error:     str  = ""


def _load() -> list[dict]:
    if SERVERS_FILE.exists():
        try:
            return json.loads(SERVERS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []


def _save(data: list):
    SERVERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    SERVERS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def get_servers() -> list[dict]:
    return _load()


def add_server(name: str, address: str, port: int = 25565,
               modpack_url: str = "") -> dict:
    host, _, p = address.partition(":")
    port = int(p) if p.isdigit() else port
    srv = {"name": name, "address": host, "port": port,
           "modpack_url": modpack_url, "favorite": False}
    data = _load()
    data.append(srv)
    _save(data)
    return srv


def remove_server(idx: int):
    data = _load()
    if 0 <= idx < len(data):
        data.pop(idx)
        _save(data)


def toggle_favorite(idx: int):
    data = _load()
    if 0 <= idx < len(data):
        data[idx]["favorite"] = not data[idx].get("favorite", False)
        _save(data)


# ── ping Minecraft server ─────────────────────────────────────────────────────

def ping_server(address: str, port: int = 25565,
                timeout: float = 3.0) -> ServerStatus:
    """Ping Minecraft server (protokół 1.7+)."""
    status = ServerStatus(address=address, port=port)
    try:
        import time
        t0  = time.time()
        sock = socket.create_connection((address, port), timeout=timeout)
        status.latency_ms = int((time.time() - t0) * 1000)

        # Handshake packet
        def _pack_varint(val: int) -> bytes:
            buf = b""
            while True:
                part = val & 0x7F
                val >>= 7
                if val:
                    part |= 0x80
                buf += bytes([part])
                if not val:
                    break
            return buf

        host_bytes  = address.encode("utf-8")
        payload = (
            _pack_varint(0x00) +               # packet id: handshake
            _pack_varint(763) +                # protocol version
            _pack_varint(len(host_bytes)) + host_bytes +
            struct.pack(">H", port) +
            _pack_varint(1)                    # next state: status
        )
        packet = _pack_varint(len(payload)) + payload
        sock.sendall(packet)

        # Status request
        sock.sendall(b"\x01\x00")

        # Read response
        def _read_varint(s):
            val, shift = 0, 0
            while True:
                b = s.recv(1)
                if not b:
                    return 0
                val |= (b[0] & 0x7F) << shift
                if not (b[0] & 0x80):
                    return val
                shift += 7

        _read_varint(sock)  # packet length
        _read_varint(sock)  # packet id
        str_len = _read_varint(sock)
        raw = b""
        while len(raw) < str_len:
            chunk = sock.recv(str_len - len(raw))
            if not chunk:
                break
            raw += chunk
        sock.close()

        import json as _json
        data = _json.loads(raw.decode("utf-8"))
        status.online      = True
        status.players     = data.get("players", {}).get("online", 0)
        status.max_players = data.get("players", {}).get("max", 0)
        status.version     = data.get("version", {}).get("name", "")
        desc = data.get("description", {})
        status.motd = desc.get("text", "") if isinstance(desc, dict) else str(desc)
        # Strip color codes
        import re
        status.motd = re.sub(r"§.", "", status.motd).strip()

    except Exception as e:
        status.online = False
        status.error  = str(e)
    return status


def ping_all_async(callback: Callable[[int, ServerStatus], None]):
    """Pinguje wszystkie serwery asynchronicznie."""
    servers = get_servers()
    for i, srv in enumerate(servers):
        def _ping(idx=i, s=srv):
            result = ping_server(s["address"], s.get("port", 25565))
            callback(idx, result)
        threading.Thread(target=_ping, daemon=True).start()


# ── One-Click Join ────────────────────────────────────────────────────────────

def prepare_join(
    server: dict,
    active_installation: dict,
    on_status: Callable[[str], None] | None = None,
) -> tuple[bool, str]:
    """
    Przygotowuje środowisko do dołączenia na serwer.
    Pobiera wymagane mody jeśli serwer ma zdefiniowany modpack.
    """
    modpack_url = server.get("modpack_url", "")
    if not modpack_url:
        return True, "Gotowe — brak wymaganych modów"

    if on_status:
        on_status("Pobieranie konfiguracji serwera…")

    try:
        import requests
        r = requests.get(modpack_url, timeout=10)
        r.raise_for_status()
        pack_data = r.json()

        from .modpack_manager import download_modpack_mods
        from .minecraft_launcher import get_instance_dir
        from .mod_library import load_settings

        inst_mods = get_instance_dir(active_installation) / "mods"
        settings  = load_settings()
        ok, errors = download_modpack_mods(
            pack_data, inst_mods, settings, on_status=on_status)
        if errors:
            return False, f"Błędy: {'; '.join(errors[:3])}"
        return True, f"Pobrano {ok} modów"
    except Exception as e:
        return False, f"Błąd: {e}"
