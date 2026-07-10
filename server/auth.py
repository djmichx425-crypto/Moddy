from datetime import datetime, timedelta, timezone
import bcrypt
from jose import jwt, JWTError
from fastapi import HTTPException, Header
from sqlalchemy.orm import Session

from .config import JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRE_DAYS
from .database import User


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_jwt(user: User) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=JWT_EXPIRE_DAYS)
    return jwt.encode({
        "sub": str(user.id),
        "username": user.username,
        "email": user.email,
        "is_premium": user.is_premium,
        "exp": expire,
    }, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_jwt(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Nieprawidłowy lub wygasły token")


def get_current_user(authorization: str = Header(...)) -> dict:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Brak tokenu")
    return decode_jwt(authorization[7:])
