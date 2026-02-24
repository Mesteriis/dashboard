from __future__ import annotations

from pathlib import Path

import yaml
from core.contracts.storage import StorageDDLSpec
from pydantic import BaseModel, Field


class _StorageDdlBundle(BaseModel):
    version: int = Field(ge=1)
    plugins: dict[str, StorageDDLSpec] = Field(default_factory=dict)


def load_storage_ddl_specs(file_path: Path) -> dict[str, StorageDDLSpec]:
    if not file_path.exists():
        return {}

    payload = yaml.safe_load(file_path.read_text(encoding="utf-8"))
    if payload is None:
        return {}

    bundle = _StorageDdlBundle.model_validate(payload)
    return dict(bundle.plugins)


__all__ = ["load_storage_ddl_specs"]
