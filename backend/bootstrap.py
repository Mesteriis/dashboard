from __future__ import annotations

from pathlib import Path

from config.container import AppContainer, build_container
from config.settings import AppSettings, load_app_settings
from core.logging_setup import configure_logging

BASE_DIR = Path(__file__).resolve().parent


def init_logging() -> None:
    configure_logging()


def load_runtime_settings(*, base_dir: Path | None = None) -> AppSettings:
    resolved_base_dir = BASE_DIR if base_dir is None else base_dir.resolve()
    return load_app_settings(base_dir=resolved_base_dir)


def build_runtime_container(*, base_dir: Path | None = None) -> AppContainer:
    resolved_base_dir = BASE_DIR if base_dir is None else base_dir.resolve()
    return build_container(base_dir=resolved_base_dir)


__all__ = [
    "BASE_DIR",
    "build_runtime_container",
    "init_logging",
    "load_runtime_settings",
]
