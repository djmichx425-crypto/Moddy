"""
Google OAuth flow dla aplikacji desktopowej.
Otwiera przeglądarkę → łapie callback na localhost:5050 → wymienia kod na JWT Moddy.
"""
import threading
import webbrowser
import urllib.parse
import secrets
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler


CALLBACK_PORT = 5050
# Google wymaga 127.0.0.1 (nie localhost) dla aplikacji desktopowych
REDIRECT_URI  = f"http://127.0.0.1:{CALLBACK_PORT}/callback"

# Adres backendu Moddy (zmień na URL produkcyjny po deployu)
SERVER_URL = "http://localhost:8000"

# Client ID z console.cloud.google.com (tylko publiczny — secret jest na serwerze)
GOOGLE_CLIENT_ID = ""  # uzupełnij lub wczytaj z ustawień


def get_auth_url(client_id: str, state: str) -> str:
    params = {
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "offline",
        "prompt": "select_account",
    }
    return "https://accounts.google.com/o/oauth2/auth?" + urllib.parse.urlencode(params)


class _CallbackHandler(BaseHTTPRequestHandler):
    """Jednorazowy handler HTTP który łapie callback od Google."""
    code: str | None = None
    error: str | None = None

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = dict(urllib.parse.parse_qsl(parsed.query))
        if "code" in params:
            _CallbackHandler.code = params["code"]
            body = b"<html><body style='font-family:sans-serif;text-align:center;padding:60px'><h2>Zalogowano pomyslnie!</h2><p>Mozesz zamknac to okno i wrocic do Moddy.</p></body></html>"
        else:
            _CallbackHandler.error = params.get("error", "unknown")
            body = b"<html><body style='font-family:sans-serif;text-align:center;padding:60px'><h2>Blad logowania</h2><p>Mozesz zamknac to okno.</p></body></html>"
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_):
        pass  # wycisz logi


def login_with_google(client_id: str, on_success, on_error):
    """
    Przeprowadza pełny flow OAuth w osobnym wątku.
    on_success(jwt_token, user_info) – wywoływane w wątku
    on_error(message)               – wywoływane w wątku
    """
    if not client_id:
        on_error("Brak GOOGLE_CLIENT_ID w konfiguracji serwera")
        return

    state = secrets.token_urlsafe(16)
    _CallbackHandler.code = None
    _CallbackHandler.error = None

    def run():
        # uruchom tymczasowy serwer HTTP
        server = HTTPServer(("127.0.0.1", CALLBACK_PORT), _CallbackHandler)
        server.timeout = 120  # czekaj max 2 minuty

        # otwórz przeglądarkę
        url = get_auth_url(client_id, state)
        webbrowser.open(url)

        # czekaj na callback
        server.handle_request()
        server.server_close()

        if _CallbackHandler.error:
            on_error(f"Google zwróciło błąd: {_CallbackHandler.error}")
            return
        if not _CallbackHandler.code:
            on_error("Nie otrzymano kodu autoryzacji")
            return

        # wymień kod na JWT Moddy
        try:
            resp = requests.post(f"{SERVER_URL}/auth/google", json={
                "code": _CallbackHandler.code,
                "redirect_uri": REDIRECT_URI,
            }, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            on_success(data["access_token"], data["user"])
        except Exception as e:
            on_error(f"Błąd serwera Moddy: {e}")

    threading.Thread(target=run, daemon=True).start()


def fetch_user_info(token: str) -> dict | None:
    """Pobierz aktualny profil użytkownika z serwera."""
    try:
        resp = requests.get(f"{SERVER_URL}/user/me",
                            headers={"Authorization": f"Bearer {token}"}, timeout=8)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return None


def check_server_online() -> bool:
    try:
        r = requests.get(f"{SERVER_URL}/health", timeout=3)
        return r.status_code == 200
    except Exception:
        return False
