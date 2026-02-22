from __future__ import annotations

import base64
import hashlib
import json
import os
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml
from pydantic import ValidationError

from db.repositories import DashboardConfigRepository, StoredDashboardConfig
from scheme.dashboard import (
    AuthProfileConfig,
    BasicAuthProfile,
    BearerAuthProfile,
    ConfigVersion,
    DashboardConfig,
    GroupBlock,
    IframeItemConfig,
    ItemConfig,
    QueryTokenAuthProfile,
    ValidationIssue,
    WidgetBlock,
)


class DashboardConfigValidationError(Exception):
    def __init__(self, issues: list[ValidationIssue]):
        super().__init__("Dashboard configuration validation failed")
        self.issues = issues


@dataclass
class DashboardConfigState:
    config: DashboardConfig
    version: ConfigVersion


@dataclass(frozen=True)
class DashboardConfigSavedEvent:
    source: str
    config: DashboardConfig
    version: ConfigVersion


def _join_path(path: tuple[Any, ...]) -> str:
    if not path:
        return "$"
    return "$." + ".".join(str(item) for item in path)


class DashboardConfigService:
    def __init__(
        self,
        config_path: Path,
        config_repository: DashboardConfigRepository | None = None,
        post_save_handlers: Iterable[Callable[[DashboardConfigSavedEvent], None]] = (),
    ):
        self.config_path = config_path
        self.config_repository = config_repository
        self._post_save_handlers = tuple(post_save_handlers)
        self._state: DashboardConfigState | None = None
        self._last_issues: list[ValidationIssue] = []

    @property
    def last_issues(self) -> list[ValidationIssue]:
        return self._last_issues.copy()

    def load(self, *, force: bool = False) -> DashboardConfig:
        try:
            if self.config_repository is not None:
                state = self._load_from_db(force=force)
            else:
                state = self._load_from_file(force=force)
        except DashboardConfigValidationError as exc:
            self._last_issues = exc.issues
            raise

        self._state = state
        self._last_issues = []
        return state.config

    def get_version(self) -> ConfigVersion:
        self.load()
        state = self._state
        if state is None:
            raise RuntimeError("Dashboard configuration state is not initialized")
        return state.version

    def validate_yaml(self, yaml_text: str) -> tuple[DashboardConfig | None, list[ValidationIssue]]:
        try:
            raw_document = yaml.safe_load(yaml_text)
        except yaml.YAMLError as exc:
            issue = ValidationIssue(code="yaml_parse_error", path="$", message=str(exc))
            return None, [issue]

        try:
            config = self._validate_document(raw_document)
        except DashboardConfigValidationError as exc:
            return None, exc.issues
        return config, []

    def save(self, raw_document: Any, *, source: str = "api") -> DashboardConfigState:
        try:
            config = self._validate_document(raw_document)
        except DashboardConfigValidationError as exc:
            self._last_issues = exc.issues
            raise

        if self.config_repository is not None:
            state = self._save_config_to_db(config=config, source=source)
        else:
            state = self._save_to_file(config)

        self._state = state
        self._last_issues = []
        self._emit_post_save(
            DashboardConfigSavedEvent(
                source=source,
                config=state.config,
                version=state.version,
            )
        )
        return state

    def export_yaml(self, config: DashboardConfig | None = None) -> str:
        target_config = config or self.load()
        return self._serialize_yaml(target_config)

    def import_yaml(self, yaml_text: str, *, source: str = "restore") -> DashboardConfigState:
        config, issues = self.validate_yaml(yaml_text)
        if config is None:
            raise DashboardConfigValidationError(issues)
        return self.save(config.model_dump(mode="json", exclude_none=True), source=source)

    def get_item(self, item_id: str) -> ItemConfig:
        config = self.load()
        for group in config.groups:
            for subgroup in group.subgroups:
                for item in subgroup.items:
                    if item.id == item_id:
                        return item
        raise KeyError(item_id)

    def list_items(self) -> list[ItemConfig]:
        config = self.load()
        return [item for group in config.groups for subgroup in group.subgroups for item in subgroup.items]

    def get_iframe_item(self, item_id: str) -> IframeItemConfig:
        item = self.get_item(item_id)
        if not isinstance(item, IframeItemConfig):
            raise TypeError(f"Item '{item_id}' is not an iframe item")
        return item

    def resolve_auth_profile(self, profile_id: str | None) -> AuthProfileConfig | None:
        if profile_id is None:
            return None

        config = self.load()
        for profile in config.security.auth_profiles:
            if profile.id == profile_id:
                return profile
        raise KeyError(profile_id)

    def build_proxy_request(self, item: IframeItemConfig) -> tuple[dict[str, str], dict[str, str]]:
        """
        Returns (headers, query_params) to apply when calling upstream iframe URL.
        """
        headers: dict[str, str] = {}
        query_params: dict[str, str] = {}

        profile = self.resolve_auth_profile(item.auth_profile)
        if profile is None:
            return headers, query_params

        if isinstance(profile, BasicAuthProfile):
            username = self._read_env(profile.username_env)
            password = self._read_env(profile.password_env)
            token = base64.b64encode(f"{username}:{password}".encode()).decode("ascii")
            headers["Authorization"] = f"Basic {token}"
            return headers, query_params

        if isinstance(profile, BearerAuthProfile):
            token = self._read_env(profile.token_env)
            headers[profile.header] = f"{profile.prefix} {token}" if profile.prefix else token
            return headers, query_params

        if isinstance(profile, QueryTokenAuthProfile):
            token = self._read_env(profile.token_env)
            query_params[profile.query_param] = token
            return headers, query_params

        return headers, query_params

    def _load_from_db(self, *, force: bool) -> DashboardConfigState:
        state = self._fetch_db_state()
        if state is None:
            state = self._bootstrap_from_yaml_to_db()

        if not force and self._state and self._state.version.sha256 == state.version.sha256:
            return self._state
        return state

    def _load_from_file(self, *, force: bool) -> DashboardConfigState:
        file_hash, file_mtime, raw_document = self._read_document()
        if not force and self._state and self._state.version.sha256 == file_hash:
            return self._state

        config = self._validate_document(raw_document)
        return DashboardConfigState(config=config, version=ConfigVersion(sha256=file_hash, mtime=file_mtime))

    def _fetch_db_state(self) -> DashboardConfigState | None:
        if self.config_repository is None:
            return None

        stored = self.config_repository.fetch_active()
        if stored is None:
            return None
        return self._state_from_stored(stored)

    def _state_from_stored(self, stored: StoredDashboardConfig) -> DashboardConfigState:
        try:
            raw_document = json.loads(stored.payload_json)
        except json.JSONDecodeError as exc:
            raise DashboardConfigValidationError(
                [
                    ValidationIssue(
                        code="invalid_stored_payload",
                        path="$.dashboard_config.payload_json",
                        message=str(exc),
                    )
                ]
            ) from exc

        config = self._validate_document(raw_document)
        mtime = stored.updated_at.timestamp() if stored.updated_at else 0.0
        return DashboardConfigState(
            config=config,
            version=ConfigVersion(sha256=stored.payload_sha256, mtime=mtime),
        )

    def _bootstrap_from_yaml_to_db(self) -> DashboardConfigState:
        _file_hash, _file_mtime, raw_document = self._read_document()
        config = self._validate_document(raw_document)
        state = self._save_config_to_db(config=config, source="bootstrap")
        self._delete_bootstrap_file()
        return state

    def _save_config_to_db(self, *, config: DashboardConfig, source: str) -> DashboardConfigState:
        if self.config_repository is None:
            raise RuntimeError("Config repository is required for DB-backed save")

        payload_json = self._serialize_json(config)
        payload_sha256 = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()
        stored = self.config_repository.save_active(
            payload_json=payload_json,
            payload_sha256=payload_sha256,
            source=source,
            now=datetime.now(UTC),
        )

        return DashboardConfigState(
            config=config,
            version=ConfigVersion(sha256=stored.payload_sha256, mtime=stored.updated_at.timestamp()),
        )

    def _save_to_file(self, config: DashboardConfig) -> DashboardConfigState:
        serialized = self._serialize_yaml(config)
        self._write_document(serialized)

        file_hash = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
        file_mtime = self.config_path.stat().st_mtime
        return DashboardConfigState(config=config, version=ConfigVersion(sha256=file_hash, mtime=file_mtime))

    @staticmethod
    def _serialize_json(config: DashboardConfig) -> str:
        return json.dumps(
            config.model_dump(mode="json", exclude_none=True),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

    @staticmethod
    def _serialize_yaml(config: DashboardConfig) -> str:
        serialized = yaml.safe_dump(
            config.model_dump(mode="json", exclude_none=True),
            sort_keys=False,
            allow_unicode=True,
            width=120,
        )
        return serialized if serialized.endswith("\n") else f"{serialized}\n"

    def _delete_bootstrap_file(self) -> None:
        try:
            self.config_path.unlink()
        except FileNotFoundError:
            return
        except OSError as exc:
            raise DashboardConfigValidationError(
                [
                    ValidationIssue(
                        code="bootstrap_cleanup_failed",
                        path=str(self.config_path),
                        message=f"Imported config into database, but failed to delete bootstrap file: {exc}",
                    )
                ]
            ) from exc

    def _read_env(self, key: str) -> str:
        value = os.getenv(key)
        if value is None:
            raise DashboardConfigValidationError(
                [
                    ValidationIssue(
                        code="missing_secret",
                        path=f"$ENV.{key}",
                        message=f"Required environment variable '{key}' is not set",
                    )
                ]
            )
        return value

    def _read_document(self) -> tuple[str, float, Any]:
        if not self.config_path.exists():
            raise DashboardConfigValidationError(
                [
                    ValidationIssue(
                        code="file_not_found",
                        path=str(self.config_path),
                        message=f"Config file not found: {self.config_path}",
                    )
                ]
            )

        raw_text = self.config_path.read_text(encoding="utf-8")
        file_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
        file_mtime = self.config_path.stat().st_mtime

        try:
            raw_document = yaml.safe_load(raw_text)
        except yaml.YAMLError as exc:
            raise DashboardConfigValidationError(
                [ValidationIssue(code="yaml_parse_error", path="$", message=str(exc))]
            ) from exc

        return file_hash, file_mtime, raw_document

    def _write_document(self, serialized_yaml: str) -> None:
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.config_path.with_suffix(f"{self.config_path.suffix}.tmp")
        tmp_path.write_text(serialized_yaml, encoding="utf-8")
        tmp_path.replace(self.config_path)

    def _validate_document(self, raw_document: Any) -> DashboardConfig:
        issues: list[ValidationIssue] = []

        if not isinstance(raw_document, dict):
            issues.append(
                ValidationIssue(
                    code="invalid_root",
                    path="$",
                    message="YAML root must be an object",
                )
            )
            raise DashboardConfigValidationError(issues)

        try:
            config = DashboardConfig.model_validate(raw_document)
        except ValidationError as exc:
            for error in exc.errors():
                issues.append(
                    ValidationIssue(
                        code="schema_error",
                        path=_join_path(tuple(error.get("loc", ()))),
                        message=error.get("msg", "invalid value"),
                    )
                )
            raise DashboardConfigValidationError(issues) from exc

        issues.extend(self._validate_cross_references(config))
        if issues:
            raise DashboardConfigValidationError(issues)
        return config

    def _validate_cross_references(self, config: DashboardConfig) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        default_sandbox = config.security.iframe.default_sandbox

        page_ids = {page.id for page in config.layout.pages}
        if len(page_ids) != len(config.layout.pages):
            issues.append(
                ValidationIssue(
                    code="duplicate_id",
                    path="$.layout.pages",
                    message="Page IDs must be unique",
                )
            )

        group_ids = {group.id for group in config.groups}
        if len(group_ids) != len(config.groups):
            issues.append(
                ValidationIssue(
                    code="duplicate_id",
                    path="$.groups",
                    message="Group IDs must be unique",
                )
            )

        subgroup_ids: set[str] = set()
        item_ids: set[str] = set()
        for group in config.groups:
            for subgroup in group.subgroups:
                if subgroup.id in subgroup_ids:
                    issues.append(
                        ValidationIssue(
                            code="duplicate_id",
                            path=f"$.groups[{group.id}].subgroups",
                            message=f"Duplicate subgroup id: {subgroup.id}",
                        )
                    )
                subgroup_ids.add(subgroup.id)

                for item in subgroup.items:
                    if item.id in item_ids:
                        issues.append(
                            ValidationIssue(
                                code="duplicate_id",
                                path=f"$.groups[{group.id}].subgroups[{subgroup.id}].items",
                                message=f"Duplicate item id: {item.id}",
                            )
                        )
                    item_ids.add(item.id)

        widget_ids = {widget.id for widget in config.widgets}
        if len(widget_ids) != len(config.widgets):
            issues.append(
                ValidationIssue(
                    code="duplicate_id",
                    path="$.widgets",
                    message="Widget IDs must be unique",
                )
            )

        valid_group_refs = group_ids | subgroup_ids
        for page in config.layout.pages:
            for block in page.blocks:
                if isinstance(block, WidgetBlock):
                    for widget_id in block.widgets:
                        if widget_id not in widget_ids:
                            issues.append(
                                ValidationIssue(
                                    code="unknown_widget",
                                    path=f"$.layout.pages[{page.id}].blocks",
                                    message=f"Unknown widget reference: {widget_id}",
                                )
                            )
                if isinstance(block, GroupBlock):
                    for group_id in block.group_ids:
                        if group_id not in valid_group_refs:
                            issues.append(
                                ValidationIssue(
                                    code="unknown_group",
                                    path=f"$.layout.pages[{page.id}].blocks",
                                    message=f"Unknown group/subgroup reference: {group_id}",
                                )
                            )

        auth_profile_ids = {profile.id for profile in config.security.auth_profiles}
        if len(auth_profile_ids) != len(config.security.auth_profiles):
            issues.append(
                ValidationIssue(
                    code="duplicate_id",
                    path="$.security.auth_profiles",
                    message="Auth profile IDs must be unique",
                )
            )

        allowed_domains = config.security.iframe.allowed_domains
        for group in config.groups:
            for subgroup in group.subgroups:
                for item in subgroup.items:
                    if isinstance(item, IframeItemConfig):
                        if item.iframe.sandbox is None:
                            item.iframe.sandbox = default_sandbox

                        if item.auth_profile and item.auth_profile not in auth_profile_ids:
                            issues.append(
                                ValidationIssue(
                                    code="unknown_auth_profile",
                                    path=f"$.groups[{group.id}].subgroups[{subgroup.id}].items[{item.id}].auth_profile",
                                    message=f"Unknown auth profile: {item.auth_profile}",
                                )
                            )

                        if allowed_domains:
                            host = (urlparse(str(item.url)).hostname or "").lower()
                            if host and not self._is_domain_allowed(host, allowed_domains):
                                issues.append(
                                    ValidationIssue(
                                        code="domain_not_allowed",
                                        path=f"$.groups[{group.id}].subgroups[{subgroup.id}].items[{item.id}].url",
                                        message=f"Iframe domain '{host}' is not in security.iframe.allowed_domains",
                                    )
                                )

        return issues

    @staticmethod
    def _is_domain_allowed(host: str, allowed_domains: list[str]) -> bool:
        for domain in allowed_domains:
            normalized = domain.lower().strip()
            if not normalized:
                continue
            normalized = normalized.lstrip(".")
            if host == normalized or host.endswith(f".{normalized}"):
                return True
        return False

    def _emit_post_save(self, event: DashboardConfigSavedEvent) -> None:
        for handler in self._post_save_handlers:
            handler(event)
