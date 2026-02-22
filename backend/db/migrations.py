from __future__ import annotations

from pathlib import Path

from alembic.config import Config

from alembic import command


def run_alembic_upgrade(*, ini_path: Path, db_url: str) -> None:
    alembic_config = Config(str(ini_path.resolve()))
    script_location = alembic_config.get_main_option("script_location")
    if script_location and not Path(script_location).is_absolute():
        alembic_config.set_main_option(
            "script_location",
            str((ini_path.resolve().parent / script_location).resolve()),
        )
    alembic_config.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(alembic_config, "head")


__all__ = ["run_alembic_upgrade"]
