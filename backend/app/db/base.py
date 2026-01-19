"""Database base and session management."""

from typing import AsyncGenerator

from sqlalchemy.orm import declarative_base

from app.config import settings

import logging

logger = logging.getLogger(__name__)


# Create declarative base for all models
Base = declarative_base()


# Async engine setup is commented out - use sync in database.py instead
# # Create async engine
# engine = create_async_engine(
#     settings.database_url,
#     echo=settings.debug,
#     future=True,
#     pool_pre_ping=True,
# )
#
# # Create async session factory
# async_session_maker = async_sessionmaker(
#     engine,
#     class_=AsyncSession,
#     expire_on_commit=False,
#     future=True,
# )
#
#
# async def init_db():
#     """Initialize database."""
#     logger.info("Initializing database...")
#     
#     try:
#         async with engine.begin() as conn:
#             await conn.run_sync(Base.metadata.create_all)
#         logger.info("✅ Database tables created/verified")
#     except Exception as e:
#         logger.error(f"❌ Database initialization failed: {e}")
#         raise
#
#
# async def get_db() -> AsyncGenerator[AsyncSession, None]:
#     """Get database session."""
#     async with async_session_maker() as session:
#         try:
#             yield session
#         finally:
#             await session.close()
