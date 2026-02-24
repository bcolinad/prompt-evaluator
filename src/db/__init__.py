"""SQLAlchemy async engine and session factory with thread-safe initialization."""

from __future__ import annotations

import threading
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.config import get_settings

_engine = None
_session_factory = None
_lock = threading.RLock()


def get_engine():
    """Get or create the async SQLAlchemy engine.

    Uses double-checked locking to ensure thread-safe singleton creation.

    Returns:
        The shared ``AsyncEngine`` instance.
    """
    global _engine
    if _engine is None:
        with _lock:
            if _engine is None:
                settings = get_settings()
                _engine = create_async_engine(
                    settings.async_database_url,
                    echo=settings.is_development,
                    pool_pre_ping=True,
                    pool_size=5,
                    max_overflow=10,
                )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Get or create the async session factory.

    Uses double-checked locking to ensure thread-safe singleton creation.

    Returns:
        The shared ``async_sessionmaker`` instance.
    """
    global _session_factory
    if _session_factory is None:
        with _lock:
            if _session_factory is None:
                _session_factory = async_sessionmaker(
                    bind=get_engine(),
                    class_=AsyncSession,
                    expire_on_commit=False,
                )
    return _session_factory


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session.

    Commits on success, rolls back on exception.

    Yields:
        An ``AsyncSession`` bound to the shared engine.
    """
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def dispose_engine() -> None:
    """Dispose the async engine and reset module-level singletons.

    Call this during graceful shutdown to release all pooled connections.
    """
    global _engine, _session_factory
    with _lock:
        if _engine is not None:
            await _engine.dispose()
        _engine = None
        _session_factory = None
