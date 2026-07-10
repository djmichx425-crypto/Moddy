import json
from pathlib import Path
from typing import Optional
from jose import jwt
from datetime import datetime, timezone

TOKEN_FILE = Path(__file__).parent.parent.parent / "app_data" / "session.json"


def save_session(token: str, user_info: dict):
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(TOKEN_FILE, "w", encoding="utf-8") as f:
        json.dump({"token": token, "user": user_info}, f, ensure_ascii=False)


def load_session() -> tuple[Optional[str], Optional[dict]]:
    if not TOKEN_FILE.exists():
        return None, None
    try:
        with open(TOKEN_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        token = data.get("token")
        user  = data.get("user")
        payload = jwt.get_unverified_claims(token)
        if datetime.now(timezone.utc).timestamp() > payload.get("exp", 0):
            clear_session()
            return None, None
        return token, user
    except Exception:
        return None, None


def clear_session():
    if TOKEN_FILE.exists():
        TOKEN_FILE.unlink()


def is_premium(user_info: Optional[dict]) -> bool:
    """Zalogowany = Premium."""
    return bool(user_info)


def get_full_tier(user_info: Optional[dict] = None) -> str:
    """
    'premium' – zalogowane konto
    'free'    – brak konta
    """
    return "premium" if user_info else "free"
