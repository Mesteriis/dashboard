from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import sessionmaker

from db.models import DashboardConfigRecord
from db.repositories import DashboardConfigRepository
from db.session import build_sqlite_engine


def _sha(char: str) -> str:
    return char * 64


@pytest.fixture()
def config_repository(tmp_path: Path) -> Iterator[DashboardConfigRepository]:
    engine: Engine = build_sqlite_engine((tmp_path / "dashboard.sqlite3").resolve())
    DashboardConfigRecord.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    try:
        yield DashboardConfigRepository(session_factory)
    finally:
        engine.dispose()


def test_fetch_active_returns_none_when_storage_is_empty(config_repository: DashboardConfigRepository) -> None:
    assert config_repository.fetch_active() is None


def test_save_active_creates_first_revision(config_repository: DashboardConfigRepository) -> None:
    now = datetime(2026, 2, 22, 12, 0, 0, tzinfo=UTC)

    stored = config_repository.save_active(
        payload_json='{"version":1}',
        payload_sha256=_sha("a"),
        source="bootstrap",
        now=now,
    )

    assert stored.revision == 1
    assert stored.payload_sha256 == _sha("a")
    assert stored.source == "bootstrap"
    assert stored.created_at == now
    assert stored.updated_at == now

    active = config_repository.fetch_active()
    assert active is not None
    assert active.revision == 1
    assert active.payload_json == '{"version":1}'

    revisions = config_repository.list_revisions()
    assert len(revisions) == 1
    assert revisions[0].revision == 1
    assert revisions[0].source == "bootstrap"
    assert revisions[0].payload_sha256 == _sha("a")


def test_save_active_increments_revision_and_appends_history(config_repository: DashboardConfigRepository) -> None:
    first_now = datetime(2026, 2, 22, 12, 0, 0, tzinfo=UTC)
    second_now = datetime(2026, 2, 22, 12, 5, 0, tzinfo=UTC)

    first = config_repository.save_active(
        payload_json='{"version":1}',
        payload_sha256=_sha("a"),
        source="bootstrap",
        now=first_now,
    )
    second = config_repository.save_active(
        payload_json='{"version":2}',
        payload_sha256=_sha("b"),
        source="api",
        now=second_now,
    )

    assert first.revision == 1
    assert second.revision == 2
    assert second.created_at == first_now
    assert second.updated_at == second_now
    assert second.payload_json == '{"version":2}'
    assert second.payload_sha256 == _sha("b")
    assert second.source == "api"

    revisions = config_repository.list_revisions()
    assert [row.revision for row in revisions] == [1, 2]
    assert [row.source for row in revisions] == ["bootstrap", "api"]
    assert revisions[0].created_at == first_now
    assert revisions[1].created_at == second_now
