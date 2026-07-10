"""
Moddy Backend
─────────────
Uruchomienie:
    py -m uvicorn server.main:app --reload --port 8000
"""
import uvicorn
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from .config import SERVER_HOST, SERVER_PORT
from .database import init_db, get_db, User, ModRating
from .auth import hash_password, verify_password, create_jwt, get_current_user

app = FastAPI(title="Moddy API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.on_event("startup")
def startup():
    init_db()


# ── modele ───────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def email_ok(cls, v):
        v = v.strip().lower()
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Nieprawidłowy adres e-mail")
        return v

    @field_validator("username")
    @classmethod
    def username_ok(cls, v):
        v = v.strip()
        if len(v) < 3:
            raise ValueError("Nazwa użytkownika min. 3 znaki")
        if len(v) > 32:
            raise ValueError("Nazwa użytkownika max. 32 znaki")
        return v

    @field_validator("password")
    @classmethod
    def password_ok(cls, v):
        if len(v) < 6:
            raise ValueError("Hasło min. 6 znaków")
        return v


class LoginRequest(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    is_premium: bool


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# ── auth ──────────────────────────────────────────────────────────────────────

@app.post("/auth/register", response_model=TokenResponse)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(400, "Ten e-mail jest już zajęty")
    if db.query(User).filter(User.username == body.username).first():
        raise HTTPException(400, "Ta nazwa użytkownika jest już zajęta")

    user = User(
        username=body.username,
        email=body.email,
        password=hash_password(body.password),
        is_premium=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return TokenResponse(
        access_token=create_jwt(user),
        user=UserResponse(id=user.id, username=user.username,
                          email=user.email, is_premium=user.is_premium),
    )


@app.post("/auth/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not verify_password(body.password, user.password):
        raise HTTPException(401, "Nieprawidłowy e-mail lub hasło")
    user.last_login = datetime.now(timezone.utc)
    db.commit()
    return TokenResponse(
        access_token=create_jwt(user),
        user=UserResponse(id=user.id, username=user.username,
                          email=user.email, is_premium=user.is_premium),
    )


@app.get("/user/me", response_model=UserResponse)
def get_me(current: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == int(current["sub"])).first()
    if not user:
        raise HTTPException(404, "Użytkownik nie istnieje")
    return UserResponse(id=user.id, username=user.username,
                        email=user.email, is_premium=user.is_premium)


@app.post("/admin/set-premium")
def set_premium(email: str, value: bool = True, db: Session = Depends(get_db),
                _: dict = Depends(get_current_user)):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(404, "Nie znaleziono użytkownika")
    user.is_premium = value
    db.commit()
    return {"ok": True, "email": email, "is_premium": value}


# ── ratings ───────────────────────────────────────────────────────────────────

class RatingRequest(BaseModel):
    source:   str
    mod_id:   str
    stars:    int
    comment:  str = ""
    mod_name: str = ""

    @field_validator("stars")
    @classmethod
    def stars_range(cls, v):
        if not 1 <= v <= 5:
            raise ValueError("Ocena musi być 1–5")
        return v


@app.post("/ratings")
def submit_rating(body: RatingRequest,
                  current: dict = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    user_id = int(current["sub"])
    existing = db.query(ModRating).filter(
        ModRating.user_id == user_id,
        ModRating.source  == body.source,
        ModRating.mod_id  == body.mod_id,
    ).first()
    if existing:
        existing.stars   = body.stars
        existing.comment = body.comment
        existing.mod_name = body.mod_name
    else:
        db.add(ModRating(user_id=user_id, source=body.source,
                         mod_id=body.mod_id, mod_name=body.mod_name,
                         stars=body.stars, comment=body.comment))
    db.commit()
    return {"ok": True}


@app.get("/ratings/{source}/{mod_id}")
def get_ratings(source: str, mod_id: str, db: Session = Depends(get_db)):
    rows = db.query(ModRating).filter(
        ModRating.source == source, ModRating.mod_id == mod_id).all()
    if not rows:
        return {"average": 0.0, "count": 0,
                "distribution": {str(i): 0 for i in range(1, 6)},
                "comments": []}
    dist = {str(i): 0 for i in range(1, 6)}
    for r in rows:
        dist[str(r.stars)] = dist.get(str(r.stars), 0) + 1
    avg = sum(r.stars for r in rows) / len(rows)
    comments = [{"stars": r.stars, "comment": r.comment,
                 "date": r.created_at.isoformat()[:10]}
                for r in rows if r.comment][-10:]
    return {"average": round(avg, 1), "count": len(rows),
            "distribution": dist, "comments": comments}


@app.get("/ratings/top")
def top_rated(limit: int = 20, db: Session = Depends(get_db)):
    from sqlalchemy import func
    rows = (db.query(
                ModRating.source, ModRating.mod_id, ModRating.mod_name,
                func.avg(ModRating.stars).label("average"),
                func.count(ModRating.id).label("count"))
            .group_by(ModRating.source, ModRating.mod_id)
            .having(func.count(ModRating.id) >= 2)
            .order_by(func.avg(ModRating.stars).desc())
            .limit(limit).all())
    return [{"source": r.source, "mod_id": r.mod_id, "mod_name": r.mod_name,
             "average": round(r.average, 1), "count": r.count}
            for r in rows]


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run("server.main:app", host=SERVER_HOST, port=SERVER_PORT, reload=True)
