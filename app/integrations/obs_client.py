"""
OBS WebSocket v5 client (OBS 28+).
Łączy się z OBS Studio przez WebSocket i steruje nagrywaniem/streamingiem.
"""
from __future__ import annotations
import base64, hashlib, json, threading, time
from typing import Callable

try:
    import websocket
    _HAS_WS = True
except ImportError:
    _HAS_WS = False


class OBSStatus:
    def __init__(self):
        self.connected       = False
        self.recording       = False
        self.streaming       = False
        self.recording_time  = ""
        self.streaming_time  = ""
        self.scene           = ""
        self.error           = ""


class OBSClient:
    """Klient OBS WebSocket v5."""

    def __init__(self, host: str = "localhost", port: int = 4455,
                 password: str = ""):
        self._host     = host
        self._port     = port
        self._password = password
        self._ws: "websocket.WebSocket | None" = None
        self._msg_id   = 0
        self._lock     = threading.Lock()
        self.status    = OBSStatus()
        self._on_status: Callable[[OBSStatus], None] | None = None

    def set_callback(self, fn: Callable[[OBSStatus], None]):
        self._on_status = fn

    # ── connect ───────────────────────────────────────────────────────────────

    def connect(self) -> bool:
        if not _HAS_WS:
            self.status.error = "Brak websocket-client"
            return False
        try:
            ws = websocket.create_connection(
                f"ws://{self._host}:{self._port}", timeout=4)
            self._ws = ws

            # Hello
            hello = json.loads(ws.recv())
            if hello.get("op") != 0:
                raise RuntimeError("Nieoczekiwana odpowiedź OBS")

            auth_data = hello.get("d", {}).get("authentication")
            auth_str  = ""
            if auth_data and self._password:
                auth_str = self._compute_auth(
                    self._password,
                    auth_data["salt"],
                    auth_data["challenge"])

            # Identify
            identify = {"op": 1, "d": {
                "rpcVersion": 1,
                "authentication": auth_str,
                "eventSubscriptions": 0b11111111111,
            }}
            ws.send(json.dumps(identify))
            identified = json.loads(ws.recv())
            if identified.get("op") != 2:
                raise RuntimeError("Uwierzytelnienie OBS nieudane")

            self.status.connected = True
            self.status.error     = ""
            self._notify()

            # Pobierz stan
            self._refresh_status()

            # Wątek nasłuchujący
            threading.Thread(target=self._listen_loop, daemon=True).start()
            return True

        except Exception as e:
            self.status.connected = False
            self.status.error     = str(e)
            self._notify()
            return False

    def disconnect(self):
        if self._ws:
            try:
                self._ws.close()
            except Exception:
                pass
            self._ws = None
        self.status.connected = False
        self._notify()

    # ── requests ──────────────────────────────────────────────────────────────

    def start_recording(self):
        self._request("StartRecord")

    def stop_recording(self):
        self._request("StopRecord")

    def toggle_recording(self):
        self._request("ToggleRecord")

    def start_streaming(self):
        self._request("StartStream")

    def stop_streaming(self):
        self._request("StopStream")

    def set_scene(self, scene_name: str):
        self._request("SetCurrentProgramScene",
                      {"sceneName": scene_name})

    def get_scenes(self) -> list[str]:
        resp = self._request_sync("GetSceneList")
        if resp:
            return [s["sceneName"]
                    for s in resp.get("d", {}).get("responseData", {})
                              .get("scenes", [])]
        return []

    # ── internals ─────────────────────────────────────────────────────────────

    def _request(self, req_type: str, data: dict | None = None):
        if not self._ws:
            return
        with self._lock:
            self._msg_id += 1
            msg = {"op": 6, "d": {
                "requestType": req_type,
                "requestId":   str(self._msg_id),
                "requestData": data or {},
            }}
            try:
                self._ws.send(json.dumps(msg))
            except Exception:
                pass

    def _request_sync(self, req_type: str, data: dict | None = None,
                      timeout: float = 3.0) -> dict | None:
        if not self._ws:
            return None
        with self._lock:
            self._msg_id += 1
            rid = str(self._msg_id)
            msg = {"op": 6, "d": {
                "requestType": req_type,
                "requestId":   rid,
                "requestData": data or {},
            }}
            try:
                self._ws.send(json.dumps(msg))
                deadline = time.time() + timeout
                while time.time() < deadline:
                    self._ws.settimeout(0.3)
                    try:
                        raw = self._ws.recv()
                        resp = json.loads(raw)
                        if (resp.get("op") == 7 and
                                resp.get("d", {}).get("requestId") == rid):
                            return resp
                    except Exception:
                        pass
            except Exception:
                pass
        return None

    def _refresh_status(self):
        resp = self._request_sync("GetRecordStatus")
        if resp:
            d = resp.get("d", {}).get("responseData", {})
            self.status.recording      = d.get("outputActive", False)
            self.status.recording_time = d.get("outputTimecode", "")

        resp2 = self._request_sync("GetStreamStatus")
        if resp2:
            d2 = resp2.get("d", {}).get("responseData", {})
            self.status.streaming      = d2.get("outputActive", False)
            self.status.streaming_time = d2.get("outputTimecode", "")

        resp3 = self._request_sync("GetCurrentProgramScene")
        if resp3:
            self.status.scene = (resp3.get("d", {})
                                      .get("responseData", {})
                                      .get("currentProgramSceneName", ""))
        self._notify()

    def _listen_loop(self):
        ws = self._ws
        while ws and self.status.connected:
            try:
                ws.settimeout(1.0)
                raw  = ws.recv()
                data = json.loads(raw)
                op   = data.get("op")

                if op == 5:   # Event
                    evt = data.get("d", {}).get("eventType", "")
                    if evt in ("RecordStateChanged", "StreamStateChanged",
                               "CurrentProgramSceneChanged"):
                        self._refresh_status()
            except websocket.WebSocketTimeoutException:
                continue
            except Exception:
                break

        self.status.connected = False
        self._notify()

    def _notify(self):
        if self._on_status:
            self._on_status(self.status)

    @staticmethod
    def _compute_auth(password: str, salt: str, challenge: str) -> str:
        secret = base64.b64encode(
            hashlib.sha256((password + salt).encode()).digest()
        ).decode()
        auth = base64.b64encode(
            hashlib.sha256((secret + challenge).encode()).digest()
        ).decode()
        return auth
