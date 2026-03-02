from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from core.config.service import ConfigService
from core.contracts.errors import ApiError
from core.contracts.models import (
    ActiveState,
    ConfigImportRequest,
    ConfigPatchRequest,
    ConfigRevision,
    ConfigRollbackRequest,
    ConfigValidateRequest,
)
from core.storage.repositories import ActiveConfigSnapshot


def _snapshot(*, revision: int = 1, payload: dict | None = None) -> ActiveConfigSnapshot:
    now = datetime.now(UTC)
    return ActiveConfigSnapshot(
        active_state=ActiveState(
            active_revision=revision,
            state_seq=revision,
            updated_at=now,
            updated_by="tester",
            reason=None,
        ),
        revision=ConfigRevision(
            revision=revision,
            parent_revision=revision - 1 if revision > 1 else None,
            sha256="a" * 64,
            source="import",
            payload=payload or {"version": 1, "app": {"id": "oko"}},
            created_at=now,
            created_by="tester",
        ),
    )


def _service(*, repo: object | None = None, bootstrap_file: Path | None = None) -> tuple[ConfigService, SimpleNamespace, SimpleNamespace]:
    repository = repo or SimpleNamespace(
        fetch_active=AsyncMock(return_value=None),
        create_revision=AsyncMock(return_value=_snapshot()),
        list_revisions=AsyncMock(return_value=[]),
        patch_active=AsyncMock(return_value=_snapshot(revision=2)),
        rollback_to=AsyncMock(return_value=_snapshot(revision=3)),
    )
    event_bus = SimpleNamespace(publish=AsyncMock())
    service = ConfigService(
        repository=repository,
        event_bus=event_bus,
        bootstrap_file=bootstrap_file or Path("/tmp/non-existent-bootstrap.yaml"),
    )
    return service, repository, event_bus


async def test_startup_bootstrap_returns_active_without_changes(tmp_path: Path) -> None:
    existing = _snapshot(revision=7)
    service, repository, event_bus = _service(
        repo=SimpleNamespace(
            fetch_active=AsyncMock(return_value=existing),
            create_revision=AsyncMock(),
            list_revisions=AsyncMock(return_value=[]),
            patch_active=AsyncMock(),
            rollback_to=AsyncMock(),
        ),
        bootstrap_file=tmp_path / "bootstrap.yaml",
    )

    response = await service.startup_bootstrap()
    assert response.active_state.active_revision == 7
    repository.create_revision.assert_not_awaited()
    event_bus.publish.assert_not_awaited()


async def test_startup_bootstrap_imports_from_file(tmp_path: Path) -> None:
    bootstrap = tmp_path / "bootstrap.yaml"
    bootstrap.write_text("version: 1\napp:\n  id: oko\n", encoding="utf-8")

    service, repository, event_bus = _service(
        repo=SimpleNamespace(
            fetch_active=AsyncMock(return_value=None),
            create_revision=AsyncMock(return_value=_snapshot(revision=1)),
            list_revisions=AsyncMock(return_value=[]),
            patch_active=AsyncMock(),
            rollback_to=AsyncMock(),
        ),
        bootstrap_file=bootstrap,
    )

    response = await service.startup_bootstrap()
    assert response.active_state.active_revision == 1
    repository.create_revision.assert_awaited_once()
    event_bus.publish.assert_awaited_once()


async def test_startup_bootstrap_creates_default_when_file_missing(tmp_path: Path) -> None:
    service, repository, event_bus = _service(
        repo=SimpleNamespace(
            fetch_active=AsyncMock(return_value=None),
            create_revision=AsyncMock(return_value=_snapshot(revision=1)),
            list_revisions=AsyncMock(return_value=[]),
            patch_active=AsyncMock(),
            rollback_to=AsyncMock(),
        ),
        bootstrap_file=tmp_path / "missing.yaml",
    )

    _ = await service.startup_bootstrap()
    repository.create_revision.assert_awaited_once()
    kwargs = repository.create_revision.await_args.kwargs
    assert kwargs["reason"] == "bootstrap_default"
    assert kwargs["payload"]["app"]["title"] == "Oko"
    event_bus.publish.assert_awaited_once()


async def test_get_active_state_and_revision_errors_when_missing() -> None:
    service, _, _ = _service(
        repo=SimpleNamespace(
            fetch_active=AsyncMock(return_value=None),
            create_revision=AsyncMock(),
            list_revisions=AsyncMock(return_value=[]),
            patch_active=AsyncMock(),
            rollback_to=AsyncMock(),
        )
    )

    with pytest.raises(ApiError) as state_err:
        await service.get_active_state()
    assert state_err.value.error.code == "state_missing"

    with pytest.raises(ApiError) as revision_err:
        await service.get_active_revision()
    assert revision_err.value.error.code == "config_missing"


async def test_import_validate_patch_and_rollback_paths() -> None:
    service, repository, event_bus = _service()

    imported = await service.import_config(
        request=ConfigImportRequest.model_construct(
            format="yaml",
            payload="version: 1\napp:\n  id: oko\n",
            source="manual",
        ),
        actor="tester",
    )
    assert imported.active_state.active_revision == 1
    assert repository.create_revision.await_args.kwargs["source"] == "import"
    event_bus.publish.assert_awaited()

    validate_failed = service.validate_config(
        request=ConfigValidateRequest.model_construct(format="yaml", payload="bad: [")
    )
    assert validate_failed.valid is False
    assert validate_failed.issues

    with pytest.raises(ApiError):
        await service.patch_config(
            request=ConfigPatchRequest.model_construct(patch="nope", source="patch"),
            actor="tester",
        )

    repository.patch_active = AsyncMock(side_effect=ValueError("broken patch"))
    with pytest.raises(ApiError) as patch_err:
        await service.patch_config(
            request=ConfigPatchRequest(patch={"version": 2}),
            actor="tester",
        )
    assert patch_err.value.error.code == "patch_invalid"

    repository.rollback_to = AsyncMock(side_effect=KeyError(777))
    with pytest.raises(ApiError) as rollback_err:
        await service.rollback(
            request=ConfigRollbackRequest(revision=777),
            actor="tester",
        )
    assert rollback_err.value.status_code == 404


async def test_widgets_registry_and_list_revisions() -> None:
    snapshot = _snapshot(
        revision=5,
        payload={
            "version": 1,
            "app": {"id": "oko"},
            "widgets": [
                {"type": "health"},
                {"type": "health"},
                {"type": "ops"},
                {"type": ""},
                "bad",
            ],
        },
    )
    service, repository, _ = _service(
        repo=SimpleNamespace(
            fetch_active=AsyncMock(return_value=snapshot),
            create_revision=AsyncMock(return_value=snapshot),
            list_revisions=AsyncMock(return_value=[snapshot.revision]),
            patch_active=AsyncMock(return_value=snapshot),
            rollback_to=AsyncMock(return_value=snapshot),
        )
    )

    widgets = await service.widgets_registry()
    assert [item.type for item in widgets] == ["health", "ops"]

    revisions = await service.list_revisions(limit=5)
    assert revisions[0]["revision"] == 5
    repository.list_revisions.assert_awaited_once_with(limit=5)


def test_validate_config_covers_schema_errors_and_bad_format() -> None:
    service, _repository, _event_bus = _service()

    missing_version = service.validate_config(
        request=ConfigValidateRequest.model_construct(
            format="json",
            payload='{"app":{"id":"oko"}}',
        )
    )
    assert missing_version.valid is False
    assert missing_version.issues[0]["code"] == "config_schema_error"

    bad_format = service.validate_config(
        request=ConfigValidateRequest.model_construct(
            format="ini",
            payload="x=1",
        )
    )
    assert bad_format.valid is False
    assert bad_format.issues[0]["code"] == "format_invalid"
