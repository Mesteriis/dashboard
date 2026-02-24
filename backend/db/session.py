from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine


def build_async_engine(database_url: str) -> AsyncEngine:
    return create_async_engine(
        database_url,
        pool_pre_ping=True,
    )


def build_async_session_factory(database_url: str) -> async_sessionmaker[AsyncSession]:
    engine = build_async_engine(database_url)
    return async_sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )


__all__ = ["build_async_engine", "build_async_session_factory"]
