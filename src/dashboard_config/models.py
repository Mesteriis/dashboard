from __future__ import annotations

from enum import Enum
from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field


class HttpMethod(str, Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"


class AppConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    tagline: str | None = None
    locale: str = "ru-RU"


class ThemeConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: Literal["dark", "light"] = "dark"
    accent: str = "#2dd4bf"
    background: str = "#050a0f"
    card: str = "rgba(255,255,255,0.04)"
    border: str = "rgba(255,255,255,0.08)"
    glow: bool = True


class GridConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    columns: int = Field(default=12, ge=1, le=48)
    gap: int = Field(default=12, ge=0, le=100)
    card_radius: int = Field(default=14, ge=0, le=64)


class UiConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    theme: ThemeConfig = Field(default_factory=ThemeConfig)
    grid: GridConfig = Field(default_factory=GridConfig)


class WidgetBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["widget_row", "widget_grid"]
    widgets: list[str] = Field(min_length=1)


class GroupBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["groups"]
    group_ids: list[str] = Field(min_length=1)


PageBlock = Annotated[WidgetBlock | GroupBlock, Field(discriminator="type")]


class PageConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    icon: str | None = None
    blocks: list[PageBlock] = Field(min_length=1)


class LayoutConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pages: list[PageConfig] = Field(min_length=1)


class HealthcheckConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["http"] = "http"
    url: AnyHttpUrl
    interval_sec: int = Field(default=30, ge=1, le=3600)
    timeout_ms: int = Field(default=1500, ge=100, le=120000)


class IframeViewConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sandbox: bool | None = None
    allow: list[str] = Field(default_factory=list)
    referrer_policy: str | None = None


class BaseItemConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    url: AnyHttpUrl
    icon: str | None = None
    tags: list[str] = Field(default_factory=list)
    open: Literal["new_tab", "same_tab"] = "new_tab"


class LinkItemConfig(BaseItemConfig):
    type: Literal["link"]
    healthcheck: HealthcheckConfig | None = None


class IframeItemConfig(BaseItemConfig):
    type: Literal["iframe"]
    iframe: IframeViewConfig = Field(default_factory=IframeViewConfig)
    auth_profile: str | None = None


ItemConfig = Annotated[LinkItemConfig | IframeItemConfig, Field(discriminator="type")]


class SubgroupConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    items: list[ItemConfig] = Field(min_length=1)


class GroupConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    icon: str | None = None
    description: str | None = None
    layout: Literal["auto", "full", "inline"] = "auto"
    subgroups: list[SubgroupConfig] = Field(min_length=1)


class WidgetActionConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    method: HttpMethod = HttpMethod.GET
    endpoint: str = Field(min_length=1)


class WidgetColumnConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str = Field(min_length=1)
    title: str = Field(min_length=1)


class WidgetDataConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: Literal["api"] = "api"
    endpoint: str = Field(min_length=1)
    refresh_sec: int = Field(default=10, ge=1, le=86400)
    mapping: dict[str, Any] | None = None
    columns: list[WidgetColumnConfig] = Field(default_factory=list)
    actions: list[WidgetActionConfig] = Field(default_factory=list)


class WidgetConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    type: str = Field(min_length=1)
    title: str = Field(min_length=1)
    icon: str | None = None
    data: WidgetDataConfig


class IframeSecurityConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    default_sandbox: bool = True
    allowed_domains: list[str] = Field(default_factory=list)


class NoneAuthProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    type: Literal["none"]


class BasicAuthProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    type: Literal["basic"]
    username_env: str = Field(min_length=1)
    password_env: str = Field(min_length=1)


class BearerAuthProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    type: Literal["bearer"]
    token_env: str = Field(min_length=1)
    header: str = "Authorization"
    prefix: str = "Bearer"


class QueryTokenAuthProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    type: Literal["query_token"]
    token_env: str = Field(min_length=1)
    query_param: str = "token"


AuthProfileConfig = Annotated[
    NoneAuthProfile | BasicAuthProfile | BearerAuthProfile | QueryTokenAuthProfile,
    Field(discriminator="type"),
]


class SecurityConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    iframe: IframeSecurityConfig = Field(default_factory=IframeSecurityConfig)
    auth_profiles: list[AuthProfileConfig] = Field(default_factory=list)


class DashboardConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = Field(default=1, ge=1)
    app: AppConfig
    ui: UiConfig
    layout: LayoutConfig
    groups: list[GroupConfig] = Field(min_length=1)
    widgets: list[WidgetConfig] = Field(default_factory=list)
    security: SecurityConfig = Field(default_factory=SecurityConfig)


class ValidationIssue(BaseModel):
    code: str
    path: str
    message: str


class ConfigVersion(BaseModel):
    sha256: str
    mtime: float


class ValidateRequest(BaseModel):
    yaml: str = Field(min_length=1)


class ValidateResponse(BaseModel):
    valid: bool
    issues: list[ValidationIssue] = Field(default_factory=list)
    config: DashboardConfig | None = None


class SaveConfigResponse(BaseModel):
    config: DashboardConfig
    version: ConfigVersion


class ItemHealthStatus(BaseModel):
    item_id: str
    ok: bool
    checked_url: str
    status_code: int | None = None
    latency_ms: int | None = None
    error: str | None = None


class DashboardHealthResponse(BaseModel):
    items: list[ItemHealthStatus] = Field(default_factory=list)


class IframeSourceResponse(BaseModel):
    item_id: str
    src: str
    proxied: bool
    auth_profile: str | None = None


class LanScanPort(BaseModel):
    port: int = Field(ge=1, le=65535)
    service: str | None = None


class LanScanMappedService(BaseModel):
    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    url: AnyHttpUrl


class LanScanHost(BaseModel):
    ip: str = Field(min_length=1)
    hostname: str | None = None
    mac_address: str | None = None
    mac_vendor: str | None = None
    device_type: str | None = None
    open_ports: list[LanScanPort] = Field(default_factory=list)
    http_services: list[LanHttpService] = Field(default_factory=list)
    dashboard_items: list[LanScanMappedService] = Field(default_factory=list)


class LanScanResult(BaseModel):
    generated_at: datetime
    duration_ms: int = Field(ge=0)
    scanned_hosts: int = Field(ge=0)
    scanned_ports: int = Field(default=0, ge=0)
    scanned_cidrs: list[str] = Field(default_factory=list)
    hosts: list[LanScanHost] = Field(default_factory=list)
    source_file: str | None = None


class LanHttpService(BaseModel):
    port: int = Field(ge=1, le=65535)
    scheme: Literal["http", "https"]
    url: str = Field(min_length=1)
    status_code: int | None = None
    title: str | None = None
    description: str | None = None
    server: str | None = None
    error: str | None = None


class LanScanStateResponse(BaseModel):
    enabled: bool = True
    scheduler: str = "asyncio"
    interval_sec: int = Field(default=1020, ge=30)
    running: bool = False
    queued: bool = False
    last_started_at: datetime | None = None
    last_finished_at: datetime | None = None
    next_run_at: datetime | None = None
    last_error: str | None = None
    result: LanScanResult | None = None


class LanScanTriggerResponse(BaseModel):
    accepted: bool
    message: str
    state: LanScanStateResponse
