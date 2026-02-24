from __future__ import annotations

import json
import tomllib
from pathlib import Path
from typing import Any

import yaml
from core.contracts.errors import ApiError
from core.contracts.models import (
    ConfigImportRequest,
    ConfigPatchRequest,
    ConfigRollbackRequest,
    ConfigStateResponse,
    ConfigValidateRequest,
    ConfigValidationResponse,
    WidgetRegistryEntry,
)
from core.events.protocols import EventPublisher
from core.storage.repositories import ActiveConfigSnapshot, ConfigRepository


class ConfigService:
    def __init__(
        self,
        *,
        repository: ConfigRepository,
        event_bus: EventPublisher,
        bootstrap_file: Path,
    ) -> None:
        self._repository = repository
        self._event_bus = event_bus
        self._bootstrap_file = bootstrap_file

    async def startup_bootstrap(self) -> ConfigStateResponse:
        active = await self._repository.fetch_active()
        if active is not None:
            return self._to_response(active)

        if self._bootstrap_file.exists():
            raw = self._bootstrap_file.read_text(encoding="utf-8")
            response = await self.import_config(
                request=ConfigImportRequest(format="yaml", payload=raw, source="bootstrap"),
                actor="system",
            )
            return response

        snapshot = await self._repository.create_revision(
            payload={"version": 1, "app": {"id": "oko", "title": "Oko"}},
            source="bootstrap",
            actor="system",
            reason="bootstrap_default",
        )
        return await self._emit_and_respond(snapshot=snapshot, event_type="core.config.bootstrap")

    async def get_active_state(self) -> ConfigStateResponse:
        snapshot = await self._repository.fetch_active()
        if snapshot is None:
            raise ApiError(status_code=500, code="state_missing", message="Active state is not initialized")
        return self._to_response(snapshot)

    async def get_active_revision(self) -> dict[str, Any]:
        snapshot = await self._repository.fetch_active()
        if snapshot is None:
            raise ApiError(status_code=500, code="config_missing", message="Active config is not initialized")
        return snapshot.revision.payload

    async def list_revisions(self, *, limit: int = 100) -> list[dict[str, Any]]:
        revisions = await self._repository.list_revisions(limit=limit)
        return [revision.model_dump(mode="json") for revision in revisions]

    async def import_config(self, *, request: ConfigImportRequest, actor: str) -> ConfigStateResponse:
        parsed = self._parse_text(request.payload, request.format)
        self._validate_payload(parsed)
        snapshot = await self._repository.create_revision(
            payload=parsed,
            source=request.source if request.source in {"bootstrap", "import", "api"} else "import",
            actor=actor,
            reason="config_import",
        )
        return await self._emit_and_respond(snapshot=snapshot, event_type="core.config.imported")

    def validate_config(self, *, request: ConfigValidateRequest) -> ConfigValidationResponse:
        try:
            parsed = self._parse_text(request.payload, request.format)
            self._validate_payload(parsed)
        except ApiError as exc:
            return ConfigValidationResponse(
                valid=False,
                issues=[
                    {
                        "code": exc.error.code,
                        "message": exc.error.message,
                    }
                ],
                config=None,
            )
        return ConfigValidationResponse(valid=True, issues=[], config=parsed)

    async def patch_config(self, *, request: ConfigPatchRequest, actor: str) -> ConfigStateResponse:
        self._validate_patch(request.patch)
        try:
            snapshot = await self._repository.patch_active(
                patch=request.patch,
                actor=actor,
                source=request.source if request.source in {"patch", "api"} else "patch",
            )
        except ValueError as exc:
            raise ApiError(status_code=422, code="patch_invalid", message=str(exc)) from exc
        self._validate_payload(snapshot.revision.payload)
        return await self._emit_and_respond(snapshot=snapshot, event_type="core.config.patched")

    async def rollback(self, *, request: ConfigRollbackRequest, actor: str) -> ConfigStateResponse:
        try:
            snapshot = await self._repository.rollback_to(
                revision=request.revision,
                actor=actor,
                source=request.source if request.source in {"rollback", "api"} else "rollback",
            )
        except KeyError as exc:
            raise ApiError(
                status_code=404,
                code="revision_not_found",
                message=f"Revision {request.revision} was not found",
            ) from exc
        return await self._emit_and_respond(snapshot=snapshot, event_type="core.config.rolled_back")

    async def widgets_registry(self) -> list[WidgetRegistryEntry]:
        snapshot = await self._repository.fetch_active()
        if snapshot is None:
            return []

        widgets = snapshot.revision.payload.get("widgets")
        if not isinstance(widgets, list):
            return []

        seen: set[str] = set()
        registry: list[WidgetRegistryEntry] = []
        for widget in widgets:
            if not isinstance(widget, dict):
                continue
            widget_type = widget.get("type")
            if not isinstance(widget_type, str) or not widget_type or widget_type in seen:
                continue
            seen.add(widget_type)
            registry.append(
                WidgetRegistryEntry(
                    type=widget_type,
                    version="1.0",
                    json_schema={},
                    capabilities=["read.widget"],
                )
            )
        return registry

    @staticmethod
    def _parse_text(payload: str, source_format: str) -> dict[str, Any]:
        try:
            if source_format == "yaml":
                parsed = yaml.safe_load(payload)
            elif source_format == "json":
                parsed = json.loads(payload)
            elif source_format == "toml":
                parsed = tomllib.loads(payload)
            else:
                raise ApiError(status_code=422, code="format_invalid", message=f"Unsupported format: {source_format}")
        except ApiError:
            raise
        except Exception as exc:
            raise ApiError(status_code=422, code="parse_failed", message=str(exc)) from exc

        if not isinstance(parsed, dict):
            raise ApiError(status_code=422, code="config_invalid_root", message="Configuration root must be an object")
        return parsed

    @staticmethod
    def _validate_patch(patch: dict[str, Any]) -> None:
        if not isinstance(patch, dict):
            raise ApiError(status_code=422, code="patch_invalid", message="Patch payload must be an object")

    @staticmethod
    def _validate_payload(payload: dict[str, Any]) -> None:
        if "version" not in payload:
            raise ApiError(status_code=422, code="config_schema_error", message="Missing required field: version")
        if "app" not in payload or not isinstance(payload.get("app"), dict):
            raise ApiError(status_code=422, code="config_schema_error", message="Missing required object: app")

    async def _emit_and_respond(self, *, snapshot: ActiveConfigSnapshot, event_type: str) -> ConfigStateResponse:
        response = self._to_response(snapshot)
        await self._event_bus.publish(
            event_type=event_type,
            source="core.config",
            payload={
                "active_revision": response.active_state.active_revision,
                "state_seq": response.active_state.state_seq,
            },
            revision=response.active_state.state_seq,
        )
        return response

    @staticmethod
    def _to_response(snapshot: ActiveConfigSnapshot) -> ConfigStateResponse:
        return ConfigStateResponse(active_state=snapshot.active_state, revision=snapshot.revision)


__all__ = ["ConfigService"]
