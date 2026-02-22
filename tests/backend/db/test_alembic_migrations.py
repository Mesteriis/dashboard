"""Tests for Alembic migration upgrade and downgrade operations."""

from __future__ import annotations

from pathlib import Path

import pytest
from alembic.command import upgrade
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.engine import Engine

from db.models import Base


@pytest.fixture
def alembic_cfg(project_root: Path, temp_db_path: Path) -> Config:
    """Create Alembic config for tests."""
    ini_path = project_root / "alembic.ini"
    cfg = Config(ini_path)
    cfg.set_main_option("script_location", str(project_root / "backend" / "alembic"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{temp_db_path}")
    return cfg


@pytest.fixture
def temp_db_path() -> Path:
    """Create a temporary database file path."""
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False) as tmp:
        db_path = Path(tmp.name)
    try:
        yield db_path
    finally:
        if db_path.exists():
            db_path.unlink()


@pytest.fixture
def temp_db_engine(temp_db_path: Path) -> Engine:
    """Create a temporary SQLite database engine."""
    from db.session import build_sqlite_engine

    engine = build_sqlite_engine(temp_db_path)
    yield engine
    engine.dispose()


@pytest.fixture
def clean_db(temp_db_engine: Engine) -> None:
    """Drop all tables before test."""
    Base.metadata.drop_all(temp_db_engine)


def get_all_revisions(alembic_cfg: Config) -> list[str]:
    """Get all migration revisions in order."""
    from alembic.script import ScriptDirectory

    script = ScriptDirectory.from_config(alembic_cfg)
    return [rev.revision for rev in script.walk_revisions()]


class TestAlembicMigrations:
    """Test Alembic migration upgrade and downgrade operations."""

    @pytest.mark.usefixtures("clean_db")
    def test_upgrade_creates_all_tables(
        self,
        alembic_cfg: Config,
        temp_db_engine: Engine,
    ) -> None:
        """Test that upgrade creates all expected tables."""
        # Run upgrade using the engine connection
        with temp_db_engine.connect() as conn:
            alembic_cfg.attributes["connection"] = conn
            upgrade(alembic_cfg, "head")
            conn.commit()

            # Check tables exist
            result = conn.execute(
                text("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
                ORDER BY name
            """)
            )
            tables = {row[0] for row in result.fetchall()}

        expected_tables = {
            "dashboard_config",
            "dashboard_config_revisions",
            "health_samples",
            "lan_scan_snapshots",
            "alembic_version",
        }

        assert tables == expected_tables

    def test_migrations_are_linear(
        self,
        alembic_cfg: Config,
    ) -> None:
        """Test that migrations form a linear chain (no branches)."""
        from alembic.script import ScriptDirectory

        script = ScriptDirectory.from_config(alembic_cfg)
        assert len(script.get_heads()) == 1

    @pytest.mark.usefixtures("clean_db")
    def test_alembic_version_table_tracks_migrations(
        self,
        alembic_cfg: Config,
        temp_db_engine: Engine,
    ) -> None:
        """Test that alembic_version table correctly tracks applied migrations."""
        with temp_db_engine.connect() as conn:
            alembic_cfg.attributes["connection"] = conn
            # Upgrade to head
            upgrade(alembic_cfg, "head")
            conn.commit()

            # Check alembic_version table
            result = conn.execute(text("SELECT version_num FROM alembic_version"))
            version_num = result.scalar()

        assert version_num is not None
        assert len(version_num) > 0
