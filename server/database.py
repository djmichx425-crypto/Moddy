from sqlalchemy import create_engine, Column, String, Boolean, DateTime, Integer, Float, Text
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime, timezone
from .config import DB_PATH

engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id         = Column(Integer, primary_key=True, index=True)
    username   = Column(String, unique=True, index=True, nullable=False)
    email      = Column(String, unique=True, index=True, nullable=False)
    password   = Column(String, nullable=False)
    is_premium = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_login = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class ModRating(Base):
    __tablename__ = "mod_ratings"

    id       = Column(Integer, primary_key=True, index=True)
    user_id  = Column(Integer, nullable=False, index=True)
    source   = Column(String, nullable=False)   # modrinth / curseforge / spiget
    mod_id   = Column(String, nullable=False, index=True)
    mod_name = Column(String, default="")
    stars    = Column(Integer, nullable=False)   # 1–5
    comment  = Column(Text, default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
