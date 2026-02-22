from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import sessionmaker

from db.models import HealthSample
from db.repositories import HealthSampleRepository, HealthSampleWrite
from db.session import build_sqlite_engine


@pytest.fixture()
def health_repository(tmp_path: Path) -> Iterator[HealthSampleRepository]:
    engine: Engine = build_sqlite_engine((tmp_path / "dashboard.sqlite3").resolve())
    HealthSample.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    try:
        yield HealthSampleRepository(session_factory)
    finally:
        engine.dispose()


def test_append_samples_persists_rows(health_repository: HealthSampleRepository) -> None:
    now = datetime(2026, 2, 22, 12, 0, 0, tzinfo=UTC)
    count = health_repository.append_samples(
        [
            HealthSampleWrite(item_id="svc-a", ts=now, level="online", latency_ms=12, status_code=200),
            HealthSampleWrite(item_id="svc-b", ts=now, level="down", latency_ms=None, status_code=503),
        ]
    )
    assert count == 2

    history = health_repository.list_recent_by_item_ids(item_ids={"svc-a", "svc-b"}, limit_per_item=5)
    assert set(history) == {"svc-a", "svc-b"}
    assert history["svc-a"][0].level == "online"
    assert history["svc-b"][0].status_code == 503


def test_list_recent_by_item_ids_applies_per_item_limit(health_repository: HealthSampleRepository) -> None:
    now = datetime(2026, 2, 22, 12, 0, 0, tzinfo=UTC)
    payload = [
        HealthSampleWrite(item_id="svc-a", ts=now + timedelta(seconds=index), level="online")
        for index in range(4)
    ]
    health_repository.append_samples(payload)

    history = health_repository.list_recent_by_item_ids(item_ids={"svc-a"}, limit_per_item=2)
    assert "svc-a" in history
    assert len(history["svc-a"]) == 2
    assert history["svc-a"][0].ts == now + timedelta(seconds=2)
    assert history["svc-a"][1].ts == now + timedelta(seconds=3)


def test_delete_samples_not_in_item_ids_removes_stale_rows(health_repository: HealthSampleRepository) -> None:
    now = datetime(2026, 2, 22, 12, 0, 0, tzinfo=UTC)
    health_repository.append_samples(
        [
            HealthSampleWrite(item_id="svc-a", ts=now, level="online"),
            HealthSampleWrite(item_id="svc-b", ts=now, level="down"),
            HealthSampleWrite(item_id="svc-c", ts=now, level="unknown"),
        ]
    )

    deleted = health_repository.delete_samples_not_in_item_ids({"svc-a", "svc-b"})
    assert deleted == 1

    history = health_repository.list_recent_by_item_ids(item_ids={"svc-a", "svc-b", "svc-c"}, limit_per_item=5)
    assert set(history) == {"svc-a", "svc-b"}
