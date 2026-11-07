from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("HD2SS_NO_HOOKS", "1")

# Never let the test suite touch the real user configuration: the app resolves
# its config folder at import time, so this must be set before any app import.
_TEST_HOME = Path(__file__).resolve().parent.parent / ".tmp" / "pytest-home"
_TEST_HOME.mkdir(parents=True, exist_ok=True)
os.environ["HD2SS_HOME"] = str(_TEST_HOME)

import pytest  # noqa: E402

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication  # noqa: E402

from app.paths import config_dir  # noqa: E402


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    """A QApplication for widget/timer tests (fonts don't matter here)."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(["pytest"])
    return app


@pytest.fixture(autouse=True, scope="session")
def _guard_config() -> None:
    """Fail loudly if the app ever resolves a config folder outside .tmp."""
    assert ".tmp" in str(config_dir()).lower(), "tests must not write the real user config"
