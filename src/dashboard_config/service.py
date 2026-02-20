from __future__ import annotations

import base64
import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml
from pydantic import ValidationError

from .models import (
    AuthProfileConfig,
    BasicAuthProfile,
    BearerAuthProfile,
    ConfigVersion,
    DashboardConfig,
    IframeItemConfig,
    ItemConfig,
    QueryTokenAuthProfile,
    ValidationIssue,
)


class DashboardConfigValidationError(Exception):
    def __init__(self, issues: list[ValidationIssue]):
        super().__init__("Dashboard configuration validation failed")
        self.issues = issues


@dataclass
class DashboardConfigState:
    config: DashboardConfig
    version: ConfigVersion


def _join_path(path: tuple[Any, ...]) -> str:
    if not path:
        return "$"
    return "$." + ".".join(str(item) for item in path)


class DashboardConfigService:
    def __init__(self, config_path: Path):
        self.config_path = config_path
        self._state: DashboardConfigState | None = None
        self._last_issues: list[ValidationIssue] = []

    @property
    def last_issues(self) -> list[ValidationIssue]:
        return list(self._last_issues)

    def load(self, *, force: bool = False) -> DashboardConfig:
        file_hash, file_mtime, raw_document = self._read_document()
        if not force and self._state and self._state.version.sha256 == file_hash:
            return self._state.config

        try:
            config = self._validate_document(raw_document)
        except DashboardConfigValidationError as exc:
            self._last_issues = exc.issues
            raise

        self._state = DashboardConfigState(config=config, version=ConfigVersion(sha256=file_hash, mtime=file_mtime))
        self._last_issues = []
        return config

    def get_version(self) -> ConfigVersion:
        if self._state is None:
            self.load()
        assert self._state is not None
        return self._state.version

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

    def get_item(self, item_id: str) -> ItemConfig:
        config = self.load()
        for group in config.groups:
            for subgroup in group.subgroups:
                for item in subgroup.items:
                    if item.id == item_id:
                        return item
        raise KeyError(item_id)

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
            token = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
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
                if hasattr(block, "widgets"):
                    for widget_id in block.widgets:
                        if widget_id not in widget_ids:
                            issues.append(
                                ValidationIssue(
                                    code="unknown_widget",
                                    path=f"$.layout.pages[{page.id}].blocks",
                                    message=f"Unknown widget reference: {widget_id}",
                                )
                            )
                if hasattr(block, "group_ids"):
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
            if host == normalized or host.endswith(f".{normalized}"):
                return True
        return False
