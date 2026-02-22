from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import sessionmaker

from db.models import LanScanSnapshot
from db.repositories import LanScanSnapshotRepository
from db.session import build_sqlite_engine


@pytest.fixture()
def scan_repository(tmp_path: Path) -> Iterator[LanScanSnapshotRepository]:
    engine: Engine = build_sqlite_engine((tmp_path / "dashboard.sqlite3").resolve())
    LanScanSnapshot.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    try:
        yield LanScanSnapshotRepository(session_factory)
    finally:
        engine.dispose()


def test_fetch_latest_returns_none_for_empty_storage(scan_repository: LanScanSnapshotRepository) -> None:
    assert scan_repository.fetch_latest() is None


def test_save_snapshot_returns_latest_entry(scan_repository: LanScanSnapshotRepository) -> None:
    first = scan_repository.save_snapshot(
        generated_at=datetime(2026, 2, 22, 12, 0, 0, tzinfo=UTC),
        payload_json='{"run":1}',
    )
    second = scan_repository.save_snapshot(
        generated_at=datetime(2026, 2, 22, 12, 10, 0, tzinfo=UTC),
        payload_json='{"run":2}',
    )

    assert first.id < second.id
    latest = scan_repository.fetch_latest()
    assert latest is not None
    assert latest.id == second.id
    assert latest.payload_json == '{"run":2}'
    assert latest.generated_at == datetime(2026, 2, 22, 12, 10, 0, tzinfo=UTC)


def test_prune_old_keeps_requested_number_of_snapshots(scan_repository: LanScanSnapshotRepository) -> None:
    for minute in range(3):
        scan_repository.save_snapshot(
            generated_at=datetime(2026, 2, 22, 12, minute, 0, tzinfo=UTC),
            payload_json=f'{{"run":{minute}}}',
        )

    deleted = scan_repository.prune_old(keep_last=2)
    assert deleted == 1

    latest = scan_repository.fetch_latest()
    assert latest is not None
    assert latest.payload_json == '{"run":2}'
