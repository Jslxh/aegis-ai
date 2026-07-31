from collections.abc import Generator
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker, declarative_base

from app.database.config import DatabaseConfig

config = DatabaseConfig()

engine = create_engine(
    config.URL,
    echo=config.ECHO,
    pool_size=config.POOL_SIZE,
    max_overflow=config.MAX_OVERFLOW,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_optional() -> Generator[Optional[Session], None, None]:
    db = None
    try:
        db = SessionLocal()
    except Exception:
        yield None
        return
    try:
        yield db
    finally:
        db.close()
