import requests

SERVER_URL = "http://localhost:8000"


def register(username: str, email: str, password: str) -> dict:
    """Zwraca {'access_token': ..., 'user': {...}} lub rzuca Exception z komunikatem."""
    r = requests.post(f"{SERVER_URL}/auth/register",
                      json={"username": username, "email": email, "password": password},
                      timeout=10)
    if r.status_code == 200:
        return r.json()
    detail = r.json().get("detail", "Błąd rejestracji")
    raise Exception(detail)


def login(email: str, password: str) -> dict:
    r = requests.post(f"{SERVER_URL}/auth/login",
                      json={"email": email, "password": password},
                      timeout=10)
    if r.status_code == 200:
        return r.json()
    detail = r.json().get("detail", "Błąd logowania")
    raise Exception(detail)


def fetch_me(token: str) -> dict | None:
    try:
        r = requests.get(f"{SERVER_URL}/user/me",
                         headers={"Authorization": f"Bearer {token}"}, timeout=6)
        return r.json() if r.status_code == 200 else None
    except Exception:
        return None


def server_online() -> bool:
    try:
        return requests.get(f"{SERVER_URL}/health", timeout=3).status_code == 200
    except Exception:
        return False
