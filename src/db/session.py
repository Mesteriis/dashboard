from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import quote

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker


def sqlite_url_from_path(path: Path) -> str:
    resolved = path.resolve()
    return f"sqlite:///{quote(str(resolved), safe='/')}"


def _apply_sqlite_pragmas(engine: Engine) -> None:
    @event.listens_for(engine, "connect")
    def _on_connect(dbapi_connection: Any, _connection_record: object) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.execute("PRAGMA busy_timeout=5000;")
        cursor.close()


def build_sqlite_engine(db_file: Path) -> Engine:
    db_file.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        sqlite_url_from_path(db_file),
        connect_args={"check_same_thread": False},
        pool_pre_ping=True,
    )
    _apply_sqlite_pragmas(engine)
    return engine


def build_sqlite_session_factory(db_file: Path) -> sessionmaker[Session]:
    engine = build_sqlite_engine(db_file)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


__all__ = ["build_sqlite_engine", "build_sqlite_session_factory", "sqlite_url_from_path"]
