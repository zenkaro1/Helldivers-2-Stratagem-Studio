"""Application entry point."""

from __future__ import annotations

import argparse
import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from . import diagnostics
from .context import AppContext
from .core.database import StratagemDatabase
from .core.storage import Storage
from .core.voice.transcribe import model_cached
from .paths import APP_NAME, APP_WINDOW_TITLE, LOGO_FILE, STRATAGEM_DB
from .ui import theme
from .ui.main_window import MainWindow


def _set_app_user_model_id() -> None:
    """Give Windows its own taskbar group/icon instead of the Python one."""
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "Arrowhead.StratagemStudio")
    except Exception:  # noqa: BLE001
        pass


def build_application(argv: list[str] | None = None) -> QApplication:
    _set_app_user_model_id()
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(argv or sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    if LOGO_FILE.exists():
        from .ui.main_window import make_app_icon

        app.setWindowIcon(make_app_icon())
    app.setStyle("Fusion")
    theme.ensure_system_fonts()
    app.setFont(theme.body_font(10))
    app.setStyleSheet(theme.STYLESHEET)
    return app


def main(argv: list[str] | None = None) -> int:
    diagnostics.install()
    parser = argparse.ArgumentParser(description="Helldivers 2 Loadout & Stratagem Studio")
    parser.add_argument("--safe", action="store_true",
                        help="keine globalen Hotkeys und keine Sprachaufnahme registrieren")
    args = parser.parse_args(argv)

    try:
        return _run(args)
    except Exception:  # noqa: BLE001 - must never die silently under pythonw
        import traceback

        diagnostics.fatal("Start fehlgeschlagen:\n\n" + traceback.format_exc())
        raise


def _acquire_instance(storage: Storage):
    """One process per user data folder; the second start focuses the first."""
    from PySide6.QtCore import QLockFile

    from .core.winutil import focus_window

    lock = QLockFile(str(storage.dir / "app.lock"))
    lock.setStaleLockTime(5000)
    if not lock.tryLock(300):
        if not focus_window(APP_WINDOW_TITLE):
            diagnostics.message(
                "Stratagem Studio",
                "Stratagem Studio läuft bereits.\n\n"
                "Bitte das Fenster im Infobereich (Tray) öffnen oder die laufende "
                "Instanz zuerst beenden – zwei Instanzen reagieren sonst beide auf "
                "dieselben Hotkeys.")
        return None
    return lock


def _run(args: argparse.Namespace) -> int:
    storage = Storage()
    instance_lock = _acquire_instance(storage)
    if instance_lock is None:
        return 0

    app = build_application([sys.argv[0]])
    database = StratagemDatabase(STRATAGEM_DB)

    settings = storage.load_settings()
    loadouts = storage.load_loadouts()

    if args.safe:
        settings.hotkeys.enabled = False
        settings.voice.enabled = False

    context = AppContext(database, storage, settings, loadouts)
    window = MainWindow(context)
    window.show()

    if not args.safe:
        context.apply_hotkeys()
        context.apply_ptt()
        diagnostics.macro_log(
            f"app started · dry_run={settings.macro.dry_run} "
            f"hold_menu={settings.macro.hold_menu} slots={settings.hotkeys.slots}")
        # Warm up only an already downloaded model; the first download stays a
        # deliberate click ("Modell vorladen") instead of a silent 500 MB fetch.
        if settings.voice.enabled and settings.voice.backend == "local":
            models_dir = storage.dir / "models"
            if model_cached(settings.voice.model, models_dir):
                context.preload_voice()

    def _cleanup() -> None:
        """Remove tray icon, overlay and hotkey timers before Qt shuts down."""
        try:
            window.prepare_exit()
        except Exception:  # noqa: BLE001
            pass
        try:
            context.shutdown()
        except Exception:  # noqa: BLE001
            pass

    app.aboutToQuit.connect(_cleanup)
    return int(app.exec())


def run_and_exit(argv: list[str] | None = None) -> int:
    """Entry point for ``python -m app``; reports failures before exiting."""
    try:
        return main(argv)
    except SystemExit as exc:  # argparse --help
        return int(exc.code or 0)
    except BaseException:  # noqa: BLE001 - already reported by diagnostics
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
