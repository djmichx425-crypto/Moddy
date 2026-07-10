import os
from pathlib import Path

# ── Google OAuth ──────────────────────────────────────────────────────────────
# Pobierz z: console.cloud.google.com → Credentials → OAuth 2.0 Client IDs
# Typ aplikacji: Desktop app
# Autoryzowany URI przekierowania: http://localhost:5050/callback
GOOGLE_CLIENT_ID     = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")

# ── JWT ───────────────────────────────────────────────────────────────────────
# Zmień na losowy długi string w produkcji
JWT_SECRET    = os.getenv("JWT_SECRET", "moddy-super-secret-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_DAYS = 30

# ── Serwer ────────────────────────────────────────────────────────────────────
SERVER_HOST = "0.0.0.0"
SERVER_PORT = int(os.getenv("PORT", "8000"))

# ── Baza danych ───────────────────────────────────────────────────────────────
_default_db = Path(os.environ.get("APPDATA", "C:/Users/Mich/AppData/Roaming")) / "moddy" / "moddy_server.db"
DB_PATH = Path(os.getenv("DB_PATH", str(_default_db)))
