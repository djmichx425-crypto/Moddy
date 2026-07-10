"""
Szyfrowanie danych lokalnych (tokeny, klucze API).
Używa Fernet (AES-128-CBC + HMAC-SHA256) z kluczem pochodnym od maszyny.
"""
from __future__ import annotations
import base64
import hashlib
import json
import os
import platform
from pathlib import Path

try:
    from cryptography.fernet import Fernet, InvalidToken
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    _HAS_CRYPTO = True
except ImportError:
    _HAS_CRYPTO = False

APPDATA       = Path(os.environ.get("APPDATA", "~"))
ENCRYPTED_DIR = APPDATA / "moddy" / "secure"
SALT_FILE     = ENCRYPTED_DIR / ".salt"


# ── key derivation ────────────────────────────────────────────────────────────

def _machine_id() -> bytes:
    """Unikalny identyfikator maszyny jako seed klucza."""
    parts = [
        platform.node(),
        platform.machine(),
        str(os.getenv("USERNAME", "user")),
        str(os.getenv("COMPUTERNAME", "pc")),
    ]
    return hashlib.sha256("|".join(parts).encode()).digest()


def _get_salt() -> bytes:
    ENCRYPTED_DIR.mkdir(parents=True, exist_ok=True)
    if SALT_FILE.exists():
        return SALT_FILE.read_bytes()
    salt = os.urandom(16)
    SALT_FILE.write_bytes(salt)
    return salt


def _derive_key() -> bytes | None:
    if not _HAS_CRYPTO:
        return None
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=_get_salt(),
        iterations=100_000,
    )
    raw = kdf.derive(_machine_id())
    return base64.urlsafe_b64encode(raw)


def _fernet() -> "Fernet | None":
    k = _derive_key()
    if k:
        return Fernet(k)
    return None


# ── API ───────────────────────────────────────────────────────────────────────

def encrypt_text(plaintext: str) -> str:
    """Szyfruje tekst. Zwraca base64-encoded ciphertext lub plaintext (fallback)."""
    f = _fernet()
    if not f:
        return plaintext
    return f.encrypt(plaintext.encode()).decode()


def decrypt_text(ciphertext: str) -> str:
    """Odszyfruje tekst. Zwraca plaintext lub oryginał przy błędzie."""
    f = _fernet()
    if not f:
        return ciphertext
    try:
        return f.decrypt(ciphertext.encode()).decode()
    except Exception:
        return ciphertext   # fallback – niezaszyfrowane stare dane


def encrypt_dict(data: dict) -> str:
    """Serializuje i szyfruje słownik."""
    return encrypt_text(json.dumps(data, ensure_ascii=False))


def decrypt_dict(ciphertext: str) -> dict:
    """Odszyfrowuje i deserializuje słownik."""
    try:
        return json.loads(decrypt_text(ciphertext))
    except Exception:
        return {}


def save_secure(name: str, data: dict):
    """Zapisuje zaszyfrowany plik w katalogu secure/."""
    ENCRYPTED_DIR.mkdir(parents=True, exist_ok=True)
    path = ENCRYPTED_DIR / f"{name}.sec"
    path.write_text(encrypt_dict(data), encoding="utf-8")


def load_secure(name: str) -> dict:
    """Wczytuje i odszyfrowuje plik z katalogu secure/."""
    path = ENCRYPTED_DIR / f"{name}.sec"
    if not path.exists():
        return {}
    return decrypt_dict(path.read_text(encoding="utf-8"))


def is_available() -> bool:
    return _HAS_CRYPTO
