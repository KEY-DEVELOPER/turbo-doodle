"""Module boundaries (CLAUDE.md 4) are enforced by import-linter; CI runs `lint-imports`.

These tests prove the contracts are live: the real tree passes, and a copy of the tree with a
forbidden import fails with a non-zero exit code (which fails the CI job).
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[2]
LINT_IMPORTS = shutil.which("lint-imports", path=str(Path(sys.executable).parent))


def _lint(root: Path) -> subprocess.CompletedProcess[str]:
    assert LINT_IMPORTS, "lint-imports not installed (uv sync)"
    env = {**os.environ, "PYTHONPATH": str(root)}
    return subprocess.run(
        [LINT_IMPORTS, "--config", str(root / ".importlinter"), "--no-cache"],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def _copy_tree(tmp_path: Path) -> Path:
    root = tmp_path / "backend"
    shutil.copytree(BACKEND_DIR / "app", root / "app", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copy(BACKEND_DIR / ".importlinter", root / ".importlinter")
    return root


def test_repository_respects_module_contracts() -> None:
    result = _lint(BACKEND_DIR)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize(
    ("module", "forbidden_import"),
    [
        ("markets", "app.identity"),  # markets knows nothing about users
        ("opportunities", "app.betting"),  # opportunities never writes bets
        ("sources", "app.events"),  # sources never writes curated tables
        ("features", "app.pato"),  # pato never feeds models
        ("settlement", "app.ledger.models"),  # settlement goes through the ledger service
        ("core", "app.markets"),  # core imports no domain module
    ],
)
def test_forbidden_import_fails_lint(tmp_path: Path, module: str, forbidden_import: str) -> None:
    root = _copy_tree(tmp_path)
    (root / "app" / module / "_violation.py").write_text(f"import {forbidden_import}\n")
    result = _lint(root)
    assert result.returncode != 0
    assert "BROKEN" in result.stdout
