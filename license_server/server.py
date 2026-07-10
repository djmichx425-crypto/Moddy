"""
Moddy License Server
Wdróż na Railway / Render / dowolny VPS.

Zmienne środowiskowe:
  ADMIN_SECRET  – sekretny token do generowania kluczy  (ZMIEŃ TO!)
  DATA_DIR      – katalog bazy SQLite (domyślnie: bieżący)
  PORT          – port HTTP (domyślnie: 8000)

Użycie (generowanie kluczy):
  curl -X POST https://TWOJ_SERWER/admin/generate \
       -H "Authorization: Bearer TWOJ_ADMIN_SECRET" \
       -H "Content-Type: application/json" \
       -d '{"count": 5, "duration_days": 30, "note": "sprzedaż marzec 2025"}'
"""
from __future__ import annotations
import os
import random
import sqlite3
import string
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

# ── config ────────────────────────────────────────────────────────────────────

DB_FILE      = Path(os.environ.get("DATA_DIR", ".")) / "licenses.db"
ADMIN_SECRET = os.environ.get("ADMIN_SECRET", "ZMIEN-TO-NA-BEZPIECZNY-SEKRET-MIN-32-ZNAKI")

app      = FastAPI(title="Moddy License Server", version="1.0.0", docs_url=None)
security = HTTPBearer()


# ── database ──────────────────────────────────────────────────────────────────

def _db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def _init_db():
    with _db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS licenses (
                key           TEXT PRIMARY KEY,
                tier          TEXT    NOT NULL DEFAULT 'pro',
                duration_days INTEGER NOT NULL DEFAULT 30,
                created_at    REAL    NOT NULL,
                activated_at  REAL,
                expires_at    REAL,
                machine_id    TEXT,
                note          TEXT
            )
        """)
        db.commit()


_init_db()


# ── helpers ───────────────────────────────────────────────────────────────────

def _gen_key() -> str:
    chars = string.ascii_uppercase + string.digits
    parts = ["".join(random.choices(chars, k=4)) for _ in range(4)]
    return "MPRO-" + "-".join(parts)


def _fmt_date(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%d.%m.%Y")


def _require_admin(creds: HTTPAuthorizationCredentials = Depends(security)):
    if creds.credentials != ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="Nieprawidłowy sekret admina")


# ── models ────────────────────────────────────────────────────────────────────

class GenerateReq(BaseModel):
    tier:         str           = "pro"
    duration_days: int          = 30
    count:        int           = 1
    note:         Optional[str] = None


class ActivateReq(BaseModel):
    key:        str
    machine_id: str


class ValidateReq(BaseModel):
    key:        str
    machine_id: str


# ── endpoints ─────────────────────────────────────────────────────────────────

@app.post("/admin/generate", dependencies=[Depends(_require_admin)])
def generate_keys(req: GenerateReq):
    """Generuje klucze licencyjne (tylko admin)."""
    now  = datetime.now(timezone.utc).timestamp()
    keys = []
    with _db() as db:
        for _ in range(min(req.count, 200)):
            key = _gen_key()
            # gwarantujemy unikalność
            while db.execute("SELECT 1 FROM licenses WHERE key=?", (key,)).fetchone():
                key = _gen_key()
            db.execute(
                "INSERT INTO licenses (key, tier, duration_days, created_at, note) "
                "VALUES (?,?,?,?,?)",
                (key, req.tier, req.duration_days, now, req.note),
            )
            keys.append(key)
        db.commit()
    return {"ok": True, "keys": keys, "tier": req.tier, "duration_days": req.duration_days}


@app.post("/activate")
def activate_key(req: ActivateReq):
    """Aktywuje klucz na urządzeniu (pierwsze wywołanie) lub potwierdza re-aktywację."""
    key = req.key.strip().upper()
    mid = req.machine_id.strip()

    with _db() as db:
        row = db.execute("SELECT * FROM licenses WHERE key=?", (key,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Klucz nie istnieje lub jest nieprawidłowy")

        now = datetime.now(timezone.utc).timestamp()

        # To samo urządzenie, klucz jeszcze ważny → zwróć bez zmiany
        if row["machine_id"] == mid and row["expires_at"] and row["expires_at"] > now:
            return {
                "ok":          True,
                "tier":        row["tier"],
                "expires_at":  row["expires_at"],
                "expires_str": _fmt_date(row["expires_at"]),
                "message":     "Klucz już aktywny na tym urządzeniu",
            }

        # Inne urządzenie → odmów (jeden klucz = jedno urządzenie)
        if row["machine_id"] and row["machine_id"] != mid:
            raise HTTPException(
                status_code=409,
                detail="Klucz jest już aktywowany na innym urządzeniu. "
                       "Napisz na support@moddy.app aby przenieść licencję.",
            )

        # Pierwsze użycie (lub klucz wygasł i re-aktywujemy na tym samym urządzeniu)
        expires_at = now + row["duration_days"] * 86400
        db.execute(
            "UPDATE licenses SET activated_at=?, expires_at=?, machine_id=? WHERE key=?",
            (now, expires_at, mid, key),
        )
        db.commit()

    return {
        "ok":          True,
        "tier":        row["tier"],
        "expires_at":  expires_at,
        "expires_str": _fmt_date(expires_at),
        "message":     "Klucz aktywowany pomyślnie",
    }


@app.post("/validate")
def validate_key(req: ValidateReq):
    """Sprawdza czy klucz jest aktywny dla danego urządzenia."""
    key = req.key.strip().upper()
    mid = req.machine_id.strip()

    with _db() as db:
        row = db.execute("SELECT * FROM licenses WHERE key=?", (key,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Klucz nie istnieje")

        now = datetime.now(timezone.utc).timestamp()

        if row["machine_id"] != mid:
            raise HTTPException(status_code=403, detail="Klucz nie należy do tego urządzenia")

        if not row["expires_at"] or row["expires_at"] <= now:
            return {"ok": False, "tier": "free", "detail": "Klucz wygasł",
                    "expires_at": row["expires_at"] or 0}

    return {
        "ok":          True,
        "tier":        row["tier"],
        "expires_at":  row["expires_at"],
        "expires_str": _fmt_date(row["expires_at"]),
    }


@app.get("/admin/list", dependencies=[Depends(_require_admin)])
def list_keys():
    """Lista wszystkich kluczy (tylko admin)."""
    with _db() as db:
        rows = db.execute(
            "SELECT key, tier, duration_days, created_at, activated_at, "
            "expires_at, machine_id, note FROM licenses ORDER BY created_at DESC"
        ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["expires_str"]   = _fmt_date(d["expires_at"])   if d["expires_at"]   else None
        d["activated_str"] = _fmt_date(d["activated_at"]) if d["activated_at"] else None
        result.append(d)
    return result


@app.delete("/admin/revoke/{key}", dependencies=[Depends(_require_admin)])
def revoke_key(key: str):
    """Dezaktywuje klucz (usuwa z bazy)."""
    key = key.strip().upper()
    with _db() as db:
        row = db.execute("SELECT 1 FROM licenses WHERE key=?", (key,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Klucz nie istnieje")
        db.execute("DELETE FROM licenses WHERE key=?", (key,))
        db.commit()
    return {"ok": True, "revoked": key}


@app.get("/health")
def health():
    return {"status": "ok", "service": "moddy-license"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
