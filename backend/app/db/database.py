"""Database module for DDAS backend."""

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

from app.config import settings
from app.db.base import Base

import logging

logger = logging.getLogger(__name__)


# Create synchronous engine (for startup/shutdown checks)
def get_engine() -> Engine:
    """Get or create database engine."""
    # Use SQLite in-memory for demo (much faster, no DB setup needed)
    logger.info("Using SQLite in-memory database for demo")
    engine = create_engine(
        "sqlite:///:memory:",
        echo=settings.debug,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    return engine


engine = get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Initialize database tables."""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables created/verified")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise


def get_db() -> Generator[Session, None, None]:
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
