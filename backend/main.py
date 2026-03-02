from __future__ import annotations

from app_factory import create_app, handle_cancelled_request
from bootstrap import BASE_DIR, build_runtime_container, init_logging, load_runtime_settings
from config.container import AppContainer

settings = load_runtime_settings(base_dir=BASE_DIR)
container: AppContainer | None = None


def _build_container() -> AppContainer:
    global container
    container = build_runtime_container(base_dir=BASE_DIR)
    return container


app = create_app(
    settings=settings,
    container_factory=_build_container,
    init_logging=init_logging,
)

__all__ = ["app", "container", "handle_cancelled_request"]
