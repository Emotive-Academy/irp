"""Test package bootstrap for irp.

Ensures the repository's 'src' directory is importable so tests can run
directly without requiring an explicit pip install step first.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

# Add project's src/ to sys.path
_ROOT = Path(__file__).resolve().parents[1]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

# External packages required for tests
EXTERNAL_TEST_REQUIREMENTS = [
    "numpy",
    "scipy",
]


def _check_requirements() -> None:
    missing = []
    for pkg in EXTERNAL_TEST_REQUIREMENTS:
        try:
            importlib.import_module(pkg)
        except Exception:
            missing.append(pkg)
    if missing:
        pkgs = " ".join(missing)
        print(
            f"[irp test bootstrap] Warning: Missing external packages: {pkgs}.\n"
            f"Install with: pip install {pkgs}",
            file=sys.stderr,
        )


_check_requirements()
