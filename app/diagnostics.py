"""Crash logging so a windowless start (pythonw) never dies silently."""

from __future__ import annotations

import sys
import traceback
from datetime import datetime
from pathlib import Path

_LOG: Path | None = None


def log_path() -> Path | None:
    global _LOG
    if _LOG is None:
        try:
            from .paths import config_dir

            _LOG = config_dir() / "crash.log"
        except OSError:
            return None
    return _LOG


def install() -> None:
    """Route uncaught exceptions (and a missing stdio) into crash.log."""
    handle = None
    path = log_path()
    if path is not None:
        try:
            handle = open(path, "a", encoding="utf-8", buffering=1)
        except OSError:
            handle = None

    if handle is not None:
        if sys.stdout is None:
            sys.stdout = handle
        if sys.stderr is None:
            sys.stderr = handle
        try:
            import faulthandler

            faulthandler.enable(handle)
        except Exception:  # noqa: BLE001 - optional safety net
            pass

    def excepthook(exc_type, exc_value, exc_tb) -> None:
        text = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if handle is not None:
            handle.write(f"\n=== {stamp} ===\n{text}")
            handle.flush()
        elif sys.__stderr__ is not None:
            sys.__stderr__.write(text)

    sys.excepthook = excepthook


def report(message: str) -> None:
    path = log_path()
    if path is None:
        return
    try:
        with open(path, "a", encoding="utf-8") as handle:
            stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            handle.write(f"[{stamp}] {message}\n")
    except OSError:
        pass


def macro_log(message: str) -> None:
    """Append a line to macro.log next to the settings (helps debug macros)."""
    try:
        from .paths import config_dir

        path = config_dir() / "macro.log"
        with open(path, "a", encoding="utf-8") as handle:
            stamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            handle.write(f"[{stamp}] {message}\n")
    except Exception:  # noqa: BLE001
        pass


def message(title: str, text: str) -> None:
    """Show a plain Windows message box (works without a Qt window)."""
    try:
        import ctypes

        ctypes.windll.user32.MessageBoxW(0, text, title, 0x40)
    except Exception:  # noqa: BLE001
        pass


def fatal(message: str) -> None:
    """Log a fatal startup error and show it even without a console."""
    report(message)
    path = log_path()
    text = message
    if path is not None:
        text += f"\n\nLog: {path}"
    try:
        import ctypes

        ctypes.windll.user32.MessageBoxW(0, text, "Stratagem Studio – Startfehler", 0x10)
    except Exception:  # noqa: BLE001 - never mask the original error
        pass
