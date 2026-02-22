from __future__ import annotations

from pathlib import Path

import pytest
from faker import Faker
from sqlalchemy import Engine
from sqlalchemy.orm import sessionmaker
from support.factories import (
    build_dashboard_config,
    build_dashboard_config_with_basic_auth,
    write_dashboard_yaml,
)

from db.models import DashboardConfigRecord
from db.repositories import DashboardConfigRepository
from db.session import build_sqlite_engine
from scheme.dashboard import (
    BearerAuthProfile,
    IframeItemConfig,
    QueryTokenAuthProfile,
    ValidationIssue,
)
from service.config_service import (
    DashboardConfigSavedEvent,
    DashboardConfigService,
    DashboardConfigValidationError,
)


def _build_config_repository(tmp_path: Path) -> tuple[DashboardConfigRepository, Engine]:
    engine = build_sqlite_engine((tmp_path / "dashboard.sqlite3").resolve())
    DashboardConfigRecord.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    return DashboardConfigRepository(session_factory), engine


def test_get_version_refreshes_after_external_file_change(tmp_path: Path, fake: Faker) -> None:
    config_path = (tmp_path / "dashboard.yaml").resolve()
    service = DashboardConfigService(config_path=config_path)

    first_config = build_dashboard_config(fake, title="First")
    write_dashboard_yaml(config_path, first_config)
    first_hash = service.get_version().sha256

    second_config = build_dashboard_config(fake, title="Second")
    write_dashboard_yaml(config_path, second_config)
    second_hash = service.get_version().sha256

    assert first_hash != second_hash


def test_load_raises_file_not_found_for_missing_yaml(tmp_path: Path) -> None:
    service = DashboardConfigService((tmp_path / "missing.yaml").resolve())
    with pytest.raises(DashboardConfigValidationError) as exc_info:
        service.load()
    assert exc_info.value.issues[0].code == "file_not_found"


def test_validate_yaml_returns_parse_error_for_invalid_yaml(tmp_path: Path) -> None:
    service = DashboardConfigService((tmp_path / "dashboard.yaml").resolve())
    config, issues = service.validate_yaml("groups: [")
    assert config is None
    assert issues[0].code == "yaml_parse_error"


def test_validate_yaml_reports_invalid_root(tmp_path: Path) -> None:
    service = DashboardConfigService((tmp_path / "dashboard.yaml").resolve())
    config, issues = service.validate_yaml("- item")
    assert config is None
    assert issues[0].code == "invalid_root"


def test_get_item_and_get_iframe_item_branches(tmp_path: Path, fake: Faker) -> None:
    config_path = (tmp_path / "dashboard.yaml").resolve()
    write_dashboard_yaml(config_path, build_dashboard_config(fake))
    service = DashboardConfigService(config_path=config_path)

    assert service.get_item("svc-link").id == "svc-link"
    with pytest.raises(KeyError):
        service.get_item("missing")

    with pytest.raises(TypeError):
        service.get_iframe_item("svc-link")
    assert service.get_iframe_item("svc-iframe-public").id == "svc-iframe-public"


def test_resolve_auth_profile_and_proxy_request_variants(
    tmp_path: Path,
    fake: Faker,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = build_dashboard_config(fake)
    iframe = config.groups[0].subgroups[0].items[2]
    assert isinstance(iframe, IframeItemConfig)
    iframe.auth_profile = None
    config.security.auth_profiles = [
        BearerAuthProfile(
            id="bearer",
            type="bearer",
            token_env="TEST_BEARER",
            header="Authorization",
            prefix="Bearer",
        ),
        QueryTokenAuthProfile(id="query", type="query_token", token_env="TEST_QUERY", query_param="token"),
    ]
    config_path = (tmp_path / "dashboard.yaml").resolve()
    write_dashboard_yaml(config_path, config)
    service = DashboardConfigService(config_path=config_path)

    iframe.auth_profile = "bearer"
    monkeypatch.setenv("TEST_BEARER", "abc")
    headers, query = service.build_proxy_request(iframe)
    assert headers["Authorization"] == "Bearer abc"
    assert query == {}

    iframe.auth_profile = "query"
    monkeypatch.setenv("TEST_QUERY", "qv")
    headers, query = service.build_proxy_request(iframe)
    assert headers == {}
    assert query == {"token": "qv"}

    iframe.auth_profile = None
    headers, query = service.build_proxy_request(iframe)
    assert headers == {}
    assert query == {}

    with pytest.raises(KeyError):
        service.resolve_auth_profile("missing")


def test_build_proxy_request_fails_fast_when_secret_is_missing(
    tmp_path: Path,
    fake: Faker,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = (tmp_path / "dashboard.yaml").resolve()
    config = build_dashboard_config_with_basic_auth(fake)
    write_dashboard_yaml(config_path, config)
    service = DashboardConfigService(config_path=config_path)
    protected_item = service.get_iframe_item("svc-iframe-protected")

    monkeypatch.delenv("TEST_IFRAME_USER", raising=False)
    monkeypatch.delenv("TEST_IFRAME_PASSWORD", raising=False)

    with pytest.raises(DashboardConfigValidationError) as exc_info:
        service.build_proxy_request(protected_item)

    assert exc_info.value.issues[0].code == "missing_secret"
    assert exc_info.value.issues[0].path.startswith("$ENV.")


def test_validate_cross_references_reports_unknown_group_and_widget(tmp_path: Path, fake: Faker) -> None:
    config = build_dashboard_config(fake)
    raw = config.model_dump(mode="json", exclude_none=True)
    raw["layout"]["pages"][0]["blocks"] = [
        {"type": "groups", "group_ids": ["missing-group"]},
        {"type": "widget_row", "widgets": ["unknown-widget"]},
    ]

    service = DashboardConfigService((tmp_path / "dashboard.yaml").resolve())
    with pytest.raises(DashboardConfigValidationError) as exc_info:
        service.save(raw)
    assert any(issue.code == "unknown_group" for issue in exc_info.value.issues)
    assert any(issue.code == "unknown_widget" for issue in exc_info.value.issues)


def test_validate_cross_references_reports_domain_and_auth_issues(tmp_path: Path, fake: Faker) -> None:
    config = build_dashboard_config(fake)
    iframe = config.groups[0].subgroups[0].items[2]
    assert isinstance(iframe, IframeItemConfig)
    iframe.auth_profile = "missing-profile"
    config.security.iframe.allowed_domains = ["allowed.local"]
    config_path = (tmp_path / "dashboard.yaml").resolve()
    write_dashboard_yaml(config_path, config)
    service = DashboardConfigService(config_path)

    with pytest.raises(DashboardConfigValidationError) as exc_info:
        service.load(force=True)

    codes = {issue.code for issue in exc_info.value.issues}
    assert "unknown_auth_profile" in codes
    assert "domain_not_allowed" in codes


def test_is_domain_allowed_supports_exact_and_subdomain() -> None:
    assert DashboardConfigService._is_domain_allowed("grafana.local", ["grafana.local"])
    assert DashboardConfigService._is_domain_allowed("a.grafana.local", ["grafana.local"])
    assert not DashboardConfigService._is_domain_allowed("grafana.com", ["grafana.local"])


def test_last_issues_property_returns_copy(tmp_path: Path) -> None:
    service = DashboardConfigService((tmp_path / "dashboard.yaml").resolve())
    service._last_issues = [ValidationIssue(code="x", path="$", message="m")]
    issues_copy = service.last_issues
    issues_copy.append(ValidationIssue(code="y", path="$", message="m"))
    assert len(service.last_issues) == 1


def test_read_document_raises_yaml_parse_error(tmp_path: Path) -> None:
    config_path = (tmp_path / "dashboard.yaml").resolve()
    config_path.write_text("version: [", encoding="utf-8")
    service = DashboardConfigService(config_path)
    with pytest.raises(DashboardConfigValidationError) as exc_info:
        service.load()
    assert exc_info.value.issues[0].code == "yaml_parse_error"


def test_save_writes_normalized_yaml_with_trailing_newline(tmp_path: Path, fake: Faker) -> None:
    config = build_dashboard_config(fake)
    service = DashboardConfigService((tmp_path / "dashboard.yaml").resolve())
    state = service.save(config.model_dump(mode="json", exclude_none=True))
    assert state.version.sha256
    raw = service.config_path.read_text(encoding="utf-8")
    assert raw.endswith("\n")


def test_db_bootstrap_imports_yaml_and_deletes_file(tmp_path: Path, fake: Faker) -> None:
    config = build_dashboard_config(fake)
    config_path = write_dashboard_yaml((tmp_path / "dashboard.yaml").resolve(), config)
    repository, engine = _build_config_repository(tmp_path)
    try:
        service = DashboardConfigService(config_path=config_path, config_repository=repository)

        loaded = service.load()

        assert loaded.app.id == config.app.id
        assert not config_path.exists()

        stored = repository.fetch_active()
        assert stored is not None
        assert stored.revision == 1
    finally:
        engine.dispose()


def test_db_save_updates_active_config_and_revision_history(tmp_path: Path, fake: Faker) -> None:
    config = build_dashboard_config(fake, title="First")
    config_path = write_dashboard_yaml((tmp_path / "dashboard.yaml").resolve(), config)
    repository, engine = _build_config_repository(tmp_path)
    try:
        service = DashboardConfigService(config_path=config_path, config_repository=repository)
        service.load()

        updated = build_dashboard_config(fake, title="Second")
        state = service.save(updated.model_dump(mode="json", exclude_none=True), source="api")

        assert state.config.app.title == "Second"

        reloaded_service = DashboardConfigService(config_path=config_path, config_repository=repository)
        reloaded = reloaded_service.load()
        assert reloaded.app.title == "Second"
        assert reloaded_service.get_version().sha256 == state.version.sha256
    finally:
        engine.dispose()


def test_db_save_is_idempotent_for_same_payload(tmp_path: Path, fake: Faker) -> None:
    config = build_dashboard_config(fake, title="Stable")
    config_path = write_dashboard_yaml((tmp_path / "dashboard.yaml").resolve(), config)
    repository, engine = _build_config_repository(tmp_path)
    try:
        service = DashboardConfigService(config_path=config_path, config_repository=repository)
        initial = service.load()

        saved = service.save(initial.model_dump(mode="json", exclude_none=True), source="api")
        repeated = service.save(initial.model_dump(mode="json", exclude_none=True), source="restore")

        assert saved.version.sha256 == repeated.version.sha256
        assert len(repository.list_revisions()) == 1
    finally:
        engine.dispose()


def test_post_save_handlers_are_called_with_saved_state(tmp_path: Path, fake: Faker) -> None:
    config = build_dashboard_config(fake, title="Handler")
    config_path = (tmp_path / "dashboard.yaml").resolve()
    captured: list[tuple[str, str]] = []

    def on_saved(event: DashboardConfigSavedEvent) -> None:
        captured.append((event.source, event.version.sha256))

    service = DashboardConfigService(
        config_path=config_path,
        post_save_handlers=[on_saved],
    )

    state = service.save(config.model_dump(mode="json", exclude_none=True), source="api")

    assert captured == [("api", state.version.sha256)]
