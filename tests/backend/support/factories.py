from __future__ import annotations

from pathlib import Path

import yaml
from faker import Faker
from polyfactory.factories.pydantic_factory import ModelFactory

from scheme.dashboard import (
    AppConfig,
    BasicAuthProfile,
    ConfigVersion,
    DashboardConfig,
    GroupBlock,
    GroupConfig,
    IframeItemConfig,
    IframeViewConfig,
    LanScanMappedService,
    LanScanPort,
    LayoutConfig,
    LinkItemConfig,
    NoneAuthProfile,
    PageConfig,
    SecurityConfig,
    SubgroupConfig,
    UiConfig,
    ValidationIssue,
)

APP_CONFIG_FACTORY = ModelFactory.create_factory(model=AppConfig)
UI_CONFIG_FACTORY = ModelFactory.create_factory(model=UiConfig)
SECURITY_CONFIG_FACTORY = ModelFactory.create_factory(model=SecurityConfig)
CONFIG_VERSION_FACTORY = ModelFactory.create_factory(model=ConfigVersion)
LAN_SCAN_PORT_FACTORY = ModelFactory.create_factory(model=LanScanPort)
LAN_SCAN_MAPPED_SERVICE_FACTORY = ModelFactory.create_factory(model=LanScanMappedService)
VALIDATION_ISSUE_FACTORY = ModelFactory.create_factory(model=ValidationIssue)


def build_dashboard_config(fake: Faker, *, title: str | None = None) -> DashboardConfig:
    app = APP_CONFIG_FACTORY.build(
        id="demo",
        title=title or fake.company(),
        tagline=fake.catch_phrase(),
        locale="ru-RU",
    )
    ui = UI_CONFIG_FACTORY.build()
    security = SECURITY_CONFIG_FACTORY.build(
        iframe={"default_sandbox": True, "allowed_domains": []},
        auth_profiles=[NoneAuthProfile(id="auth-none", type="none")],
    )

    domain = fake.domain_name()
    group_id = "core"
    subgroup_id = "core.main"

    items = [
        LinkItemConfig(
            id="svc-link",
            type="link",
            title="Main Service",
            url=f"https://{domain}/",
            tags=["core"],
            open="new_tab",
        ),
        IframeItemConfig(
            id="svc-iframe-public",
            type="iframe",
            title="Public Iframe",
            url=f"https://{domain}/public/",
            iframe=IframeViewConfig(sandbox=True, allow=["fullscreen"], referrer_policy="strict-origin"),
            tags=["iframe"],
            open="same_tab",
        ),
        IframeItemConfig(
            id="svc-iframe-protected",
            type="iframe",
            title="Protected Iframe",
            url=f"https://{domain}/protected/",
            iframe=IframeViewConfig(sandbox=True, allow=["fullscreen"], referrer_policy="strict-origin"),
            auth_profile="auth-none",
            tags=["iframe", "private"],
            open="same_tab",
        ),
    ]

    subgroup = SubgroupConfig(id=subgroup_id, title="Main", items=items)
    group = GroupConfig(id=group_id, title="Core", subgroups=[subgroup], layout="auto")
    page = PageConfig(
        id="home",
        title="Home",
        blocks=[GroupBlock(type="groups", group_ids=[group_id])],
    )
    layout = LayoutConfig(pages=[page])

    return DashboardConfig(
        version=1,
        app=app,
        ui=ui,
        layout=layout,
        groups=[group],
        widgets=[],
        security=security,
    )


def build_dashboard_config_with_basic_auth(
    fake: Faker,
    *,
    username_env: str = "TEST_IFRAME_USER",
    password_env: str = "TEST_IFRAME_PASSWORD",
) -> DashboardConfig:
    config = build_dashboard_config(fake)
    protected_item = config.groups[0].subgroups[0].items[2]
    assert isinstance(protected_item, IframeItemConfig)

    protected_item.auth_profile = "auth-basic"
    config.security.auth_profiles = [
        BasicAuthProfile(
            id="auth-basic",
            type="basic",
            username_env=username_env,
            password_env=password_env,
        )
    ]
    return config


def dump_dashboard_yaml(config: DashboardConfig) -> str:
    serialized = yaml.safe_dump(
        config.model_dump(mode="json", exclude_none=True),
        sort_keys=False,
        allow_unicode=True,
        width=120,
    )
    return serialized if serialized.endswith("\n") else f"{serialized}\n"


def write_dashboard_yaml(path: Path, config: DashboardConfig) -> Path:
    resolved = path.resolve()
    resolved.write_text(dump_dashboard_yaml(config), encoding="utf-8")
    return resolved
