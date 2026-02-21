from __future__ import annotations

from pathlib import Path

import pytest
from faker import Faker


@pytest.fixture(scope="session")
def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


@pytest.fixture()
def fake() -> Faker:
    generator = Faker("ru_RU")
    generator.seed_instance(20260221)
    return generator
