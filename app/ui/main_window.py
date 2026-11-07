"""Main window: chrome, navigation, tray icon and overlay wiring."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QPushButton,
    QStackedWidget,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from ..context import AppContext
from ..core.models import Stratagem
from ..paths import APP_WINDOW_TITLE, LOGO_FILE, LOGO_ICO_FILE, LOGO_MARK_FILE
from . import theme
from .pages.loadout_page import LoadoutPage
from .pages.macros_page import MacrosPage
from .pages.settings_page import SettingsPage
from .pages.voice_page import VoicePage
from .widgets import InAppToast, NavButton, StatusPill, VoiceOverlay

NAV = [
    ("LOADOUT", "Einsatz"),
    ("MAKROS", "Steuerung"),
    ("STIMME", "Sprache"),
    ("SYSTEM", "Einstellungen"),
]


def make_app_icon() -> QIcon:
    if LOGO_ICO_FILE.exists():
        icon = QIcon(str(LOGO_ICO_FILE))
        if not icon.isNull():
            return icon
    if LOGO_FILE.exists():
        base = QPixmap(str(LOGO_FILE))
        if not base.isNull():
            icon = QIcon()
            for size in (16, 24, 32, 48, 64, 128, 256):
                icon.addPixmap(base.scaled(
                    size, size, Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation))
            return icon
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setBrush(QColor("#11130e"))
    painter.setPen(QPen(QColor(theme.ACCENT), 2))
    painter.drawRoundedRect(2, 2, 60, 60, 10, 10)
    painter.setPen(QPen(QColor(theme.ACCENT), 6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
                        Qt.PenJoinStyle.RoundJoin))
    painter.drawLine(20, 18, 32, 30)
    painter.drawLine(44, 18, 32, 30)
    painter.drawLine(32, 30, 32, 48)
    painter.end()
    return QIcon(pixmap)


class MainWindow(QMainWindow):
    def __init__(self, ctx: AppContext):
        super().__init__()
        self.ctx = ctx
        self.setWindowTitle(APP_WINDOW_TITLE)
        self.setWindowIcon(make_app_icon())
        self.resize(1440, 900)
        self.setMinimumSize(1280, 860)

        self.overlay = VoiceOverlay()
        self.tray: QSystemTrayIcon | None = None
        self._tray_hint_shown = False
        self._build()
        self.toast = InAppToast(self)
        self._wire()
        self._build_tray()
        self._warn_low_integrity()

    def _warn_low_integrity(self) -> None:
        """A Low-integrity process cannot reach the game's window (UIPI)."""
        from ..core.winutil import is_low_integrity

        if not is_low_integrity():
            return
        message = (
            "Die App läuft mit niedrigen Rechten – Windows blockiert dann Tastatur "
            "und Makros gegenüber dem Spiel. Bitte fix_integrity.cmd als "
            "Administrator ausführen und die App neu starten.")
        self.footer_text.setText(message)
        QTimer.singleShot(
            900, lambda: self.toast.show_message("Niedrige Rechte", message, 12000))

    # ------------------------------------------------------------------
    def _build(self) -> None:
        central = QWidget()
        central.setObjectName("root")
        central.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        top = QFrame()
        top.setFixedHeight(76)
        top.setStyleSheet(f"background: rgba(9, 10, 7, 0.6); border-bottom: 1px solid {theme.BORDER};")
        top_layout = QHBoxLayout(top)
        top_layout.setContentsMargins(26, 12, 26, 12)
        top_layout.setSpacing(14)

        brand = QVBoxLayout()
        brand.setSpacing(0)
        kicker = QLabel("HELLDIVERS 2  //  TAKTIK-WERKZEUG")
        kicker.setObjectName("kicker")
        title = QLabel("STRATAGEM STUDIO")
        title.setStyleSheet(
            f"color: {theme.TEXT}; font-size: 19pt; font-weight: 600; letter-spacing: 2.5px;"
        )
        brand.addWidget(kicker)
        brand.addWidget(title)

        self.logo_label = QLabel()
        self.logo_label.setFixedSize(54, 54)
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if LOGO_MARK_FILE.exists():
            mark = QPixmap(str(LOGO_MARK_FILE))
            if not mark.isNull():
                self.logo_label.setPixmap(mark.scaled(
                    52, 52, Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation))
        top_layout.addWidget(self.logo_label, 0, Qt.AlignmentFlag.AlignVCenter)
        top_layout.addSpacing(2)
        top_layout.addLayout(brand)
        top_layout.addStretch(1)

        self.status = StatusPill()
        top_layout.addWidget(self.status, 0, Qt.AlignmentFlag.AlignVCenter)

        self.dry_badge = QLabel("TESTMODUS")
        self.dry_badge.setStyleSheet(
            f"color: {theme.RED}; border: 1px solid {theme.RED}; padding: 3px 9px;"
            " font-size: 7.5pt; font-weight: 600; letter-spacing: 1.8px;")
        self.dry_badge.setVisible(self.ctx.settings.macro.dry_run)
        top_layout.addWidget(self.dry_badge, 0, Qt.AlignmentFlag.AlignVCenter)

        self.hotkey_toggle = QPushButton()
        self.hotkey_toggle.setObjectName("ghost")
        self.hotkey_toggle.setCheckable(True)
        self.hotkey_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.hotkey_toggle.clicked.connect(self._toggle_hotkeys)
        top_layout.addWidget(self.hotkey_toggle, 0, Qt.AlignmentFlag.AlignVCenter)
        self._sync_hotkey_toggle()
        outer.addWidget(top)

        content = QHBoxLayout()
        content.setContentsMargins(0, 0, 0, 0)
        content.setSpacing(0)

        sidebar = QFrame()
        sidebar.setFixedWidth(196)
        sidebar.setStyleSheet(
            f"background: rgba(10, 11, 8, 0.5); border-right: 1px solid {theme.BORDER};"
        )
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(0, 14, 0, 14)
        side_layout.setSpacing(2)
        self.stack = QStackedWidget()
        self.pages = [
            LoadoutPage(self.ctx),
            MacrosPage(self.ctx),
            VoicePage(self.ctx),
            SettingsPage(self.ctx),
        ]
        self.nav_buttons: list[NavButton] = []
        for index, (page, (label, _)) in enumerate(zip(self.pages, NAV)):
            button = NavButton(index + 1, label)
            button.clicked.connect(lambda _=False, i=index: self._select(i))
            side_layout.addWidget(button)
            self.nav_buttons.append(button)
            self.stack.addWidget(page)
        side_layout.addStretch(1)

        self.side_status = QLabel("")
        self.side_status.setWordWrap(True)
        self.side_status.setStyleSheet(
            f"color: {theme.MUTED}; font-size: 8pt; padding: 0 16px; letter-spacing: 1px;"
        )
        side_layout.addWidget(self.side_status)
        version = QLabel("v1.0  ·  OFFLINE-FIRST")
        version.setStyleSheet(
            f"color: #565a4c; font-size: 7.5pt; padding: 4px 16px 0 16px; letter-spacing: 1.5px;"
        )
        side_layout.addWidget(version)

        content.addWidget(sidebar)
        content.addWidget(self.stack, 1)
        outer.addLayout(content, 1)

        footer = QFrame()
        footer.setFixedHeight(30)
        footer.setStyleSheet(f"border-top: 1px solid {theme.BORDER}; background: rgba(9, 10, 7, 0.6);")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(26, 0, 26, 0)
        self.footer_text = QLabel("Bereit.")
        self.footer_text.setStyleSheet(f"color: {theme.MUTED}; font-size: 8pt; letter-spacing: 0.6px;")
        footer_layout.addWidget(self.footer_text)
        footer_layout.addStretch(1)
        self.footer_hint = QLabel("")
        self.footer_hint.setStyleSheet(f"color: #565a4c; font-size: 8pt; letter-spacing: 1px;")
        footer_layout.addWidget(self.footer_hint)
        outer.addWidget(footer)

        self._select(0)
        self._update_footer_hint()

    def _select(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        for position, button in enumerate(self.nav_buttons):
            button.setChecked(position == index)

    def _update_footer_hint(self) -> None:
        hotkeys = self.ctx.settings.hotkeys
        parts = [
            f"{combo.upper()} → SLOT {index + 1}"
            for index, combo in enumerate(hotkeys.slots)
            if combo
        ]
        parts.append(f"{self.ctx.settings.voice.ptt_key.upper()} → STIMME")
        self.footer_hint.setText("   ·   ".join(parts))

    # ------------------------------------------------------------------
    def _wire(self) -> None:
        ctx = self.ctx
        ctx.executed.connect(self._on_executed)
        ctx.runner.busy_changed.connect(self._on_busy)
        ctx.voice_state.connect(self._on_voice_state)
        ctx.voice_match.connect(self._on_voice_match)
        ctx.error.connect(self._on_error)
        ctx.info.connect(self._on_info)
        ctx.hotkey_errors.connect(self._on_hotkey_errors)
        ctx.settings_changed.connect(self._sync_hotkey_toggle)
        ctx.settings_changed.connect(self._update_footer_hint)
        ctx.settings_changed.connect(self._sync_dry_badge)
        ctx.loadout_changed.connect(self._update_side_status)
        self._update_side_status()

    def _update_side_status(self) -> None:
        loadout = self.ctx.loadout
        filled = sum(1 for slot in loadout.slots if slot)
        self.side_status.setText(
            f"AKTIVES LOADOUT\n{loadout.name.upper()}\n{filled}/4 SLOTS BELEGT"
        )

    def _sync_hotkey_toggle(self) -> None:
        enabled = self.ctx.settings.hotkeys.enabled
        self.hotkey_toggle.blockSignals(True)
        self.hotkey_toggle.setChecked(enabled)
        self.hotkey_toggle.blockSignals(False)
        self.hotkey_toggle.setText("HOTKEYS: AN" if enabled else "HOTKEYS: AUS")

    def _sync_dry_badge(self) -> None:
        dry = self.ctx.settings.macro.dry_run
        self.dry_badge.setVisible(dry)
        if dry:
            self.footer_text.setText(
                "TESTMODUS aktiv – Makros senden keine Tasten an das Spiel.")

    def _toggle_hotkeys(self) -> None:
        self.ctx.settings.hotkeys.enabled = self.hotkey_toggle.isChecked()
        self.ctx.save_settings()
        self.ctx.apply_hotkeys()
        self._sync_hotkey_toggle()

    # ------------------------------------------------------------------
    def _on_executed(self, stratagem: Stratagem, source: str) -> None:
        self.footer_text.setText(f"Ausgeführt: {stratagem.name}  ({stratagem.code_pretty})")
        if self.ctx.settings.show_overlay and source == "voice":
            self.overlay.show_stratagem(stratagem, f"Sprachbefehl  ·  {stratagem.cooldown_text}")
        if source == "test":
            self.overlay.show_text("TESTLAUF", stratagem.name, stratagem.code_pretty, 1400)

    def _on_busy(self, busy: bool) -> None:
        self.status.set_state("busy" if busy else "idle", "MAKRO LÄUFT" if busy else "BEREIT")

    def _on_voice_state(self, state: str) -> None:
        if state == "listening":
            self.status.set_state("listening", "HÖRT ZU")
        elif state == "transcribing":
            self.status.set_state("transcribing", "ERKENNT …")
        elif state == "loading":
            self.status.set_state("transcribing", "MODELL …")
        elif state == "error":
            self.status.set_state("error", "FEHLER")
        else:
            self.status.set_state("idle", "BEREIT")

    def _on_voice_match(self, match) -> None:
        if match.stratagem is not None or match.slot is not None:
            return
        if not self.ctx.settings.show_overlay:
            return
        if match.outside_loadout is not None:
            self.overlay.show_text(
                "NICHT IM LOADOUT",
                match.outside_loadout.name,
                f"„{match.spoken}“ – ins Loadout legen oder Filter ausschalten",
                2600,
            )
            return
        alternatives = ", ".join(name for name, _ in match.alternatives[:2])
        self.overlay.show_text(
            "NICHT ERKANNT",
            f"„{match.spoken}“" if match.spoken else "Keine Sprache erkannt",
            alternatives,
            2200,
        )

    def _on_error(self, message: str) -> None:
        self.footer_text.setText(f"Fehler: {message}")
        self.status.set_state("error", "FEHLER")
        QTimer.singleShot(4000, lambda: self.status.set_state("idle", "BEREIT"))
        self.toast.show_message("Nicht möglich", message)
        if self.ctx.settings.notifications and self.tray is not None:
            self.tray.showMessage("Stratagem Studio", message, QSystemTrayIcon.MessageIcon.Warning, 4000)

    def _on_info(self, message: str) -> None:
        self.footer_text.setText(message)

    def _on_hotkey_errors(self, errors: list) -> None:
        if errors:
            self.footer_text.setText("Hotkey-Problem: " + "; ".join(str(e) for e in errors))
            if self.ctx.settings.notifications and getattr(self, "tray", None):
                self.tray.showMessage(
                    "Hotkey-Problem", "; ".join(str(e) for e in errors),
                    QSystemTrayIcon.MessageIcon.Warning, 5000,
                )

    # ------------------------------------------------------------------
    def _build_tray(self) -> None:
        self.tray: QSystemTrayIcon | None = None
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        self.tray = QSystemTrayIcon(make_app_icon(), self)
        menu = QMenu()
        show_action = QAction("Fenster anzeigen", self)
        show_action.triggered.connect(self.show_and_raise)
        menu.addAction(show_action)
        self.tray_toggle = QAction("Hotkeys aktiv", self, checkable=True)
        self.tray_toggle.setChecked(self.ctx.settings.hotkeys.enabled)
        self.tray_toggle.triggered.connect(self._toggle_hotkeys_from_tray)
        menu.addAction(self.tray_toggle)
        menu.addSeparator()
        quit_action = QAction("Beenden", self)
        quit_action.triggered.connect(self._quit)
        menu.addAction(quit_action)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

    def _toggle_hotkeys_from_tray(self, checked: bool) -> None:
        self.ctx.settings.hotkeys.enabled = checked
        self.ctx.save_settings()
        self.ctx.apply_hotkeys()
        self._sync_hotkey_toggle()

    def _on_tray_activated(self, reason) -> None:
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            self.show_and_raise()

    def show_and_raise(self) -> None:
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _quit(self) -> None:
        QApplication.quit()

    def prepare_exit(self) -> None:
        """Remove shell/window state before the process terminates."""
        self.overlay.hide()
        if self.tray is not None:
            self.tray.hide()
            self.tray.setVisible(False)

    def closeEvent(self, event) -> None:  # noqa: N802
        if self.ctx.settings.minimize_to_tray and self.tray is not None:
            event.ignore()
            self.hide()
            if not self._tray_hint_shown:
                self._tray_hint_shown = True
                self.tray.showMessage(
                    "Stratagem Studio",
                    "Läuft weiter im Hintergrund. Hotkeys bleiben aktiv.",
                    QSystemTrayIcon.MessageIcon.Information,
                    3000,
                )
            return
        self.prepare_exit()
        self.ctx.hotkeys.clear()
        self.ctx.ptt.unbind()
        event.accept()
