"""
Zarządzanie licencją Moddy.

Tiery:
  free  – brak konta
  plus  – zalogowane konto (darmowe)
  pro   – aktywowany klucz MPRO-xxxx-xxxx-xxxx-xxxx (30 dni)
"""
from __future__ import annotations
import hashlib
import json
import os
import platform
import re
import time
from pathlib import Path

import requests

LICENSE_FILE   = Path(os.environ.get("APPDATA", "~")) / "moddy" / "license.json"
LICENSE_SERVER = os.environ.get("MODDY_LICENSE_URL", "https://moddy-license.up.railway.app")
CACHE_TTL      = 86400   # 24 h – jak długo cache jest świeży bez odpytywania serwera
KEY_PATTERN    = re.compile(r"^MPRO-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}$")
BETA_PATTERN   = re.compile(r"^BETA-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}$")
_BETA_SECRET   = "MODDY-BETA-2025-INTERNAL"  # zmień przed release produkcyjnym


# ── beta keys (offline, bez serwera) ─────────────────────────────────────────

def generate_beta_key() -> str:
    """
    Generuje lokalny klucz beta (weryfikowalny offline).
    Uruchom:  python -c "from app.core.license_manager import generate_beta_key; print(generate_beta_key())"
    """
    import random
    import string
    chars  = string.ascii_uppercase + string.digits
    groups = ["".join(random.choices(chars, k=4)) for _ in range(3)]
    body   = "-".join(groups)
    chk    = hashlib.sha256((_BETA_SECRET + body).encode()).hexdigest()[:4].upper()
    return f"BETA-{chk}-{body}"


def _verify_beta_key(key: str) -> bool:
    parts = key.split("-")
    if len(parts) != 5 or parts[0] != "BETA":
        return False
    chk_given = parts[1]
    body       = "-".join(parts[2:])
    chk_expect = hashlib.sha256((_BETA_SECRET + body).encode()).hexdigest()[:4].upper()
    return chk_given == chk_expect


# ── machine ID ────────────────────────────────────────────────────────────────

def machine_id() -> str:
    """Deterministyczny hash identyfikujący urządzenie (nie wysyła prywatnych danych)."""
    parts = [
        platform.node(),
        platform.machine(),
        platform.processor(),
        os.environ.get("COMPUTERNAME", ""),
        os.environ.get("USERNAME", ""),
    ]
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:32]


# ── cache lokalny ─────────────────────────────────────────────────────────────

def _load_cache() -> dict:
    try:
        with open(LICENSE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_cache(data: dict):
    LICENSE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LICENSE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ── publiczne API ─────────────────────────────────────────────────────────────

def get_license_key() -> str | None:
    """Zwraca zapisany klucz lub None."""
    return _load_cache().get("key")


def get_license_expires_str() -> str:
    """Zwraca czytelną datę wygaśnięcia lub ''."""
    return _load_cache().get("expires_str", "")


def get_cached_tier() -> str:
    """
    Zwraca tier tylko z cache (bez sieciowego zapytania).
    Używaj przy starcie – żeby nie blokować UI.
    """
    cache = _load_cache()
    if not cache.get("key"):
        return "free"
    if cache.get("tier") == "pro" and cache.get("expires_at", 0) > time.time():
        return "pro"
    return "free"


def validate_key(key: str) -> tuple[bool, str, dict]:
    """
    Aktywuje klucz z serwerem licencji.
    Zwraca: (ok, komunikat, info_dict)
    info_dict zawiera: tier, expires_at (unix), expires_str (DD.MM.YYYY)
    """
    key = key.strip().upper()

    # ── klucze BETA (offline, bez serwera) ────────────────────────────────
    if BETA_PATTERN.match(key):
        if not _verify_beta_key(key):
            return False, "Nieprawidłowy klucz beta.", {}
        expires_at = time.time() + 365 * 86400  # 1 rok
        _save_cache({
            "key":         key,
            "tier":        "pro",
            "expires_at":  expires_at,
            "expires_str": "Beta (1 rok)",
            "cached_at":   time.time(),
            "beta":        True,
        })
        return True, "Aktywowano Moddy Pro (Beta)!\nDostęp przez 1 rok.", {
            "tier": "pro", "expires_at": expires_at, "expires_str": "Beta (1 rok)"}

    if not KEY_PATTERN.match(key):
        return (
            False,
            "Nieprawidłowy format klucza.\nOczekiwany: MPRO-XXXX-XXXX-XXXX-XXXX lub BETA-XXXX-XXXX-XXXX-XXXX",
            {},
        )

    try:
        r = requests.post(
            f"{LICENSE_SERVER}/activate",
            json={"key": key, "machine_id": machine_id()},
            timeout=12,
        )
        data = r.json()
        if r.status_code == 200 and data.get("ok"):
            info = {
                "tier":        data["tier"],
                "expires_at":  data["expires_at"],
                "expires_str": data.get("expires_str", ""),
            }
            _save_cache({
                "key":         key,
                "tier":        data["tier"],
                "expires_at":  data["expires_at"],
                "expires_str": data.get("expires_str", ""),
                "cached_at":   time.time(),
            })
            return (
                True,
                f"Aktywowano Moddy Pro!\nWażny do: {data.get('expires_str', '')}",
                info,
            )
        msg = data.get("detail", "Błąd aktywacji klucza")
        return False, msg, {}

    except requests.exceptions.ConnectionError:
        return False, "Brak połączenia z serwerem licencji.\nSprawdź internet.", {}
    except requests.exceptions.Timeout:
        return False, "Timeout – serwer licencji nie odpowiada.", {}
    except Exception as e:
        return False, f"Błąd: {e}", {}


def refresh_license() -> str:
    """
    Sprawdza ważność licencji z serwerem (jeśli cache jest przeterminowany).
    Zwraca aktualny tier: 'free' | 'pro'.
    Przeznaczony do wywołania w tle przy starcie.
    """
    cache = _load_cache()
    key   = cache.get("key")
    if not key:
        return "free"

    # Świeży cache – ufamy mu bez odpytywania
    if time.time() - cache.get("cached_at", 0) < CACHE_TTL:
        if cache.get("tier") == "pro" and cache.get("expires_at", 0) > time.time():
            return "pro"
        return "free"

    # Odśwież z serwerem
    try:
        r = requests.post(
            f"{LICENSE_SERVER}/validate",
            json={"key": key, "machine_id": machine_id()},
            timeout=8,
        )
        data = r.json()
        if r.status_code == 200 and data.get("ok"):
            _save_cache({
                **cache,
                "tier":        data["tier"],
                "expires_at":  data["expires_at"],
                "expires_str": data.get("expires_str", ""),
                "cached_at":   time.time(),
            })
            if data["tier"] == "pro" and data["expires_at"] > time.time():
                return "pro"
        else:
            _save_cache({**cache, "tier": "free", "cached_at": time.time()})
    except Exception:
        # Offline – ufaj staremu cache (może wygasły klucz, dajemy wolność offline)
        if cache.get("tier") == "pro" and cache.get("expires_at", 0) > time.time():
            return "pro"

    return "free"


def revoke_license():
    """Usuwa lokalnie zapisaną licencję."""
    if LICENSE_FILE.exists():
        LICENSE_FILE.unlink()
