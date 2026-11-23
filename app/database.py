"""
Database configuration and session management using SQLAlchemy ORM.
"""

import os
from pathlib import Path
from typing import Generator
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session

# Always load .env from the project root directory regardless of current working directory
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# Read DATABASE_URL from .env with fallback to default PostgreSQL connection
DEFAULT_DATABASE_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/summarizer_db"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL).strip()

# If using SQLite for testing/local offline runs, configure thread safety check
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

# Create SQLAlchemy Engine
engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,  # Automatically detects disconnected/stale connections
)

# SessionLocal class is a factory for new Session objects
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy ORM models.
    Inherits from SQLAlchemy 2.0 DeclarativeBase.
    """
    pass


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that yields a SQLAlchemy database session for each request.
    Ensures the session is cleanly closed when the request concludes.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
