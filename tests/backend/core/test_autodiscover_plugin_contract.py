from __future__ import annotations

import ast
import importlib
from pathlib import Path

import pytest


pytestmark = pytest.mark.skip(
    reason="features.autodiscover module not yet implemented",
)


def _assert_no_forbidden_imports(module_path: Path, blocked_roots: set[str]) -> None:
    source = module_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(module_path))

    for ast_node in ast.walk(tree):
        if isinstance(ast_node, ast.Import):
            for alias in ast_node.names:
                root = alias.name.split(".")[0]
                message = f"Forbidden internal import in plugin module {module_path.name}: {alias.name}"
                assert root not in blocked_roots, message
        elif isinstance(ast_node, ast.ImportFrom):
            if ast_node.module is None:
                continue
            root = ast_node.module.split(".")[0]
            message = f"Forbidden internal import in plugin module {module_path.name}: {ast_node.module}"
            assert root not in blocked_roots, message


def test_autodiscover_runtime_modules_are_self_contained() -> None:
    package = importlib.import_module("features.autodiscover")
    package_dir = Path(str(package.__file__)).resolve().parent

    blocked_roots = {
        "api",
        "config",
        "core",
        "db",
        "depens",
        "features",
        "main",
        "scheme",
        "service",
        "tools",
    }

    runtime_files = sorted(path for path in package_dir.glob("*.py") if path.name not in {"__init__.py", "registry.py"})
    assert runtime_files, "Expected autodiscover runtime files to exist"
    for module_path in runtime_files:
        _assert_no_forbidden_imports(module_path, blocked_roots)
