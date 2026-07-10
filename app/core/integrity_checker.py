"""
Weryfikacja integralności plików modów.
Przechowuje SHA-256 każdego pobranego moda i weryfikuje przed uruchomieniem.
"""
from __future__ import annotations
import hashlib
import json
import os
import zipfile
import re
from pathlib import Path
from dataclasses import dataclass, field

APPDATA      = Path(os.environ.get("APPDATA", "~"))
HASHES_FILE  = APPDATA / "moddy" / "file_hashes.json"
LIBRARY_DIR  = APPDATA / "moddy" / "library"

# Podejrzane wzorce w nazwach klas Java (RAT, keylogger, miner)
SUSPICIOUS_PATTERNS = [
    r"keylog",   r"keystroke", r"screenshot.*upload", r"sendkey",
    r"clipboard.*send", r"xmrig", r"miner", r"stratum\+tcp",
    r"discord.*token.*steal", r"grabber", r"webhook.*discord",
    r"upload.*password", r"stealer", r"inject.*dll",
    r"runtime\.exec", r"processbuilder.*cmd",
    r"obfuscat",
]


@dataclass
class IntegrityResult:
    filename:   str
    status:     str   # "ok" | "modified" | "missing" | "suspicious"
    hash_ok:    bool  = True
    threats:    list[str] = field(default_factory=list)
    message:    str   = ""


# ── hashing ───────────────────────────────────────────────────────────────────

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_hashes() -> dict:
    if HASHES_FILE.exists():
        try:
            with open(HASHES_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_hashes(data: dict):
    HASHES_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(HASHES_FILE, "w") as f:
        json.dump(data, f, indent=2)


def register_file(filename: str) -> str:
    """Rejestruje hash pobranego pliku. Wywołaj zaraz po pobraniu."""
    path = LIBRARY_DIR / filename
    if not path.exists():
        return ""
    h = sha256_file(path)
    data = _load_hashes()
    data[filename] = h
    _save_hashes(data)
    return h


def verify_file(filename: str) -> IntegrityResult:
    """Sprawdza czy plik nie został zmodyfikowany od pobrania."""
    path = LIBRARY_DIR / filename
    if not path.exists():
        return IntegrityResult(filename, "missing", False,
                               message="Plik nie istnieje")
    stored = _load_hashes().get(filename)
    if not stored:
        # Brak referencji → zarejestruj teraz
        register_file(filename)
        return IntegrityResult(filename, "ok", True,
                               message="Brak referencji — zarejestrowano")
    current = sha256_file(path)
    if current != stored:
        return IntegrityResult(filename, "modified", False,
                               message=f"Hash niezgodny!\nOczekiwany: {stored[:16]}…\nAktualny:   {current[:16]}…")
    return IntegrityResult(filename, "ok", True)


def verify_all_library() -> list[IntegrityResult]:
    results = []
    for f in LIBRARY_DIR.glob("*.jar"):
        results.append(verify_file(f.name))
    return results


# ── JAR scanner ───────────────────────────────────────────────────────────────

def scan_jar(filename: str) -> IntegrityResult:
    """
    Skanuje plik JAR w poszukiwaniu podejrzanych klas/wzorców.
    Sprawdza nazwy klas, stringi w bytecode i manifest.
    """
    path = LIBRARY_DIR / filename
    if not path.exists():
        return IntegrityResult(filename, "missing", message="Plik nie istnieje")

    threats: list[str] = []

    try:
        with zipfile.ZipFile(path, "r") as jar:
            names = jar.namelist()

            # Sprawdź nazwy klas
            for name in names:
                n_lower = name.lower()
                for pat in SUSPICIOUS_PATTERNS:
                    if re.search(pat, n_lower):
                        threats.append(f"Podejrzana klasa: {name}")
                        break

            # Sprawdź zawartość plików .class (pierwsze 4KB)
            for name in names:
                if not name.endswith(".class"):
                    continue
                try:
                    data = jar.read(name)[:4096].decode("latin-1", errors="ignore")
                    for pat in SUSPICIOUS_PATTERNS:
                        if re.search(pat, data, re.IGNORECASE):
                            threats.append(f"Podejrzana treść w: {name}")
                            break
                except Exception:
                    pass

            # Sprawdź MANIFEST.MF
            if "META-INF/MANIFEST.MF" in names:
                manifest = jar.read("META-INF/MANIFEST.MF").decode("utf-8", errors="ignore")
                if re.search(r"Main-Class.*Runtime|ProcessBuilder", manifest):
                    threats.append("Podejrzany MANIFEST.MF")

    except zipfile.BadZipFile:
        threats.append("Uszkodzony plik JAR")
    except Exception as e:
        threats.append(f"Błąd skanowania: {e}")

    if threats:
        # Deduplikuj
        threats = list(dict.fromkeys(threats))[:8]
        return IntegrityResult(filename, "suspicious", True, threats,
                               f"{len(threats)} podejrzanych wzorców")
    return IntegrityResult(filename, "ok", True, message="Brak zagrożeń")


def scan_all_library() -> list[IntegrityResult]:
    results = []
    for f in LIBRARY_DIR.glob("*.jar"):
        r = scan_jar(f.name)
        if r.status == "suspicious":
            results.append(r)
    return results
