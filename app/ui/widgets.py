"""Reusable widgets: code strips, slot cards, hotkey editors, overlay."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import (
    QEasingCurve,
    QPoint,
    QPropertyAnimation,
    QRectF,
    QSize,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import (
    QColor,
    QFont,
    QGuiApplication,
    QPainter,
    QPen,
    QPixmap,
)
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ..core.hotkeys import KeyCapture
from ..core.keymap import pretty_key
from ..core.models import ARROW_GLYPHS, Stratagem, category_color, category_label
from ..paths import ICON_DIR
from . import theme

_ICON_CACHE: dict[tuple[str, int], QPixmap] = {}


def icon_pixmap(icon: str, size: int) -> QPixmap:
    key = (icon, size)
    cached = _ICON_CACHE.get(key)
    if cached is not None:
        return cached
    path = ICON_DIR / Path(icon).name if icon else None
    pixmap = QPixmap()
    if path is not None and path.exists():
        renderer = QSvgRenderer(str(path))
        if renderer.isValid():
            ratio = 2
            pixmap = QPixmap(size * ratio, size * ratio)
            pixmap.fill(Qt.GlobalColor.transparent)
            pixmap.setDevicePixelRatio(ratio)
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            renderer.render(painter, QRectF(0, 0, size, size))
            painter.end()
    _ICON_CACHE[key] = pixmap
    return pixmap


class CodeStrip(QWidget):
    """Paints the stratagem input as arrow chips."""

    def __init__(self, code: str = "", chip: int = 24, gap: int = 5,
                 color: str = theme.ACCENT, parent: QWidget | None = None):
        super().__init__(parent)
        self._code = code
        self._chip = chip
        self._gap = gap
        self._color = color
        self.setFixedHeight(chip + 4)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._update_geometry()

    def set_code(self, code: str, color: str | None = None) -> None:
        self._code = code
        if color:
            self._color = color
        self.setToolTip(" ".join(ARROW_GLYPHS[c] for c in code))
        self._update_geometry()
        self.update()

    def _update_geometry(self) -> None:
        count = len(self._code)
        width = count * self._chip + max(0, count - 1) * self._gap if count else 0
        self.setFixedWidth(width)

    def paintEvent(self, _event) -> None:  # noqa: N802
        if not self._code:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        font = QFont(self.font())
        font.setPointSizeF(10.5)
        font.setBold(True)
        painter.setFont(font)
        x = 0.0
        for char in self._code:
            rect = QRectF(x, 2, self._chip, self._chip)
            painter.setBrush(theme.alpha(self._color, 0.10))
            painter.setPen(QPen(theme.alpha(self._color, 0.55), 1))
            painter.drawRoundedRect(rect, 2.5, 2.5)
            painter.setPen(QColor(self._color))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, ARROW_GLYPHS[char])
            x += self._chip + self._gap


class HotkeyBadge(QLabel):
    def __init__(self, text: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("hotkeyBadge")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setText(text)

    def set_key(self, key: str) -> None:
        self.setVisible(bool(key))
        self.setText(pretty_key(key))


class SlotCard(QFrame):
    clicked = Signal(int)
    clear_requested = Signal(int)

    def __init__(self, index: int, parent: QWidget | None = None):
        super().__init__(parent)
        self.index = index
        self.setObjectName("slotCard")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setProperty("empty", True)
        self.setProperty("filled", False)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumSize(198, 232)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(236)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        top = QHBoxLayout()
        top.setSpacing(6)
        self.number = QLabel(f"{index + 1:02d}")
        self.number.setObjectName("kicker")
        self.number.setStyleSheet(f"color: {theme.ACCENT}; font-size: 10pt; letter-spacing: 1px;")
        self.hotkey = HotkeyBadge("")
        top.addWidget(self.number)
        top.addStretch(1)
        top.addWidget(self.hotkey)
        layout.addLayout(top)

        icon_row = QHBoxLayout()
        icon_row.setSpacing(10)
        self.icon = QLabel()
        self.icon.setFixedSize(56, 56)
        self.icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon.setStyleSheet(f"border: 1px solid {theme.BORDER}; background: #0c0e09;")
        self.name = QLabel("Stratagem wählen")
        self.name.setObjectName("cardTitle")
        self.name.setWordWrap(True)
        self.name.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        icon_row.addWidget(self.icon)
        icon_row.addWidget(self.name, 1)
        layout.addLayout(icon_row)

        layout.addStretch(1)
        self.code_label = QLabel("INPUT-CODE")
        self.code_label.setObjectName("count")
        self.code_label.setStyleSheet(f"color: {theme.MUTED}; font-size: 7.5pt; letter-spacing: 2px;")
        layout.addWidget(self.code_label)
        self.code = CodeStrip("", chip=24, gap=5)
        layout.addWidget(self.code)

        bottom = QHBoxLayout()
        self.category = QLabel("")
        self.category.setObjectName("count")
        self.cooldown = QLabel("")
        self.cooldown.setObjectName("count")
        bottom.addWidget(self.category)
        bottom.addStretch(1)
        bottom.addWidget(self.cooldown)
        layout.addLayout(bottom)

        self._stratagem: Stratagem | None = None
        self._refresh_style()

    # ------------------------------------------------------------------
    def set_stratagem(self, stratagem: Stratagem | None, hotkey: str = "") -> None:
        self._stratagem = stratagem
        self.hotkey.set_key(hotkey)
        if stratagem is None:
            self.setProperty("empty", True)
            self.setProperty("filled", False)
            self.icon.setPixmap(QPixmap())
            self.icon.setText("+")
            self.icon.setStyleSheet(
                f"border: 1px dashed {theme.BORDER_LIGHT}; color: {theme.MUTED};"
                "font-size: 20pt; background: transparent;"
            )
            self.name.setText("Stratagem wählen")
            self.name.setStyleSheet(f"color: {theme.MUTED}; font-size: 10.5pt;")
            self.code.set_code("")
            self.category.setText("")
            self.cooldown.setText("")
            self._refresh_style()
            return

        self.setProperty("empty", False)
        self.setProperty("filled", True)
        self.icon.setStyleSheet(f"border: 1px solid {theme.BORDER}; background: #0c0e09;")
        self.icon.setPixmap(icon_pixmap(stratagem.icon, 52))
        self.name.setText(stratagem.name)
        self.name.setStyleSheet(f"color: {theme.TEXT}; font-size: 10.5pt; font-weight: 600;")
        color = category_color(stratagem.category)
        self.code.set_code(stratagem.code, color)
        self.category.setText(category_label(stratagem.category).upper())
        self.category.setStyleSheet(f"color: {theme.alpha(color, 0.9).name()}; letter-spacing: 1.5px;")
        self.cooldown.setText(stratagem.cooldown_text.upper())
        self._refresh_style()

    def set_cooldown(self, text: str) -> None:
        self.cooldown.setText(text)

    def _refresh_style(self) -> None:
        style = self.style()
        style.unpolish(self)
        style.polish(self)
        self.update()

    # ------------------------------------------------------------------
    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton and self.rect().contains(event.position().toPoint()):
            self.clicked.emit(self.index)
        super().mouseReleaseEvent(event)

    def contextMenuEvent(self, event) -> None:  # noqa: N802
        if self._stratagem is not None:
            self.clear_requested.emit(self.index)
        event.accept()


class QuickCard(QFrame):
    clicked = Signal(str)

    def __init__(self, key: str, label: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.key = key
        self.setObjectName("cardAlt")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(66)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(10)
        self.icon = QLabel()
        self.icon.setFixedSize(40, 40)
        self.icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.icon)
        text_box = QVBoxLayout()
        text_box.setSpacing(1)
        self.hotkey = QLabel("")
        self.hotkey.setObjectName("kicker")
        self.hotkey.setStyleSheet(f"color: {theme.ACCENT}; font-size: 8pt;")
        self.name = QLabel(label)
        self.name.setStyleSheet(f"color: {theme.TEXT}; font-size: 9.5pt;")
        text_box.addWidget(self.hotkey)
        text_box.addWidget(self.name)
        layout.addLayout(text_box, 1)

    def set_stratagem(self, stratagem: Stratagem | None, hotkey: str) -> None:
        self.hotkey.setText(pretty_key(hotkey) if hotkey else "")
        if stratagem is None:
            self.name.setText("nicht belegt")
            self.name.setStyleSheet(f"color: {theme.MUTED}; font-size: 9.5pt;")
            self.icon.setPixmap(QPixmap())
            return
        self.name.setText(stratagem.name)
        self.name.setStyleSheet(f"color: {theme.TEXT}; font-size: 9.5pt;")
        self.icon.setPixmap(icon_pixmap(stratagem.icon, 36))
        self.setToolTip(f"{stratagem.name}\n{stratagem.code_pretty}")

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.key)
        super().mouseReleaseEvent(event)


class NavButton(QPushButton):
    def __init__(self, index: int, label: str, parent: QWidget | None = None):
        super().__init__(f"{index:02d}   {label}", parent)
        self.setObjectName("nav")
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(46)


class HotkeyEdit(QPushButton):
    """Click, press a key combination, done."""

    changed = Signal(str)

    def __init__(self, key: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("hotkeyEdit")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumWidth(112)
        self.setFixedHeight(30)
        self._key = ""
        self._capture = KeyCapture(self)
        self._capture.captured.connect(self._on_captured)
        self._capture.cancelled.connect(self._on_cancelled)
        self.clicked.connect(self._start_capture)
        self.set_key(key)

    @property
    def key(self) -> str:
        return self._key

    def set_key(self, key: str) -> None:
        self._key = (key or "").strip().lower()
        self.setProperty("capturing", False)
        self._restyle()
        self.setText(pretty_key(self._key) if self._key else "—")

    def _start_capture(self) -> None:
        self.setProperty("capturing", True)
        self._restyle()
        self.setText("TASTE DRÜCKEN …")
        self._capture.start()

    def _on_captured(self, combo: str) -> None:
        if combo == "esc":
            self._on_cancelled()
            return
        self._key = combo
        self.setProperty("capturing", False)
        self._restyle()
        self.setText(pretty_key(combo))
        self.changed.emit(combo)

    def _on_cancelled(self) -> None:
        self.setProperty("capturing", False)
        self._restyle()
        self.setText(pretty_key(self._key) if self._key else "—")

    def _restyle(self) -> None:
        self.style().unpolish(self)
        self.style().polish(self)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.RightButton:
            self.set_key("")
            self.changed.emit("")
            return
        super().mousePressEvent(event)


class StatusPill(QFrame):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setFixedHeight(28)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 12, 0)
        layout.setSpacing(7)
        self.dot = QLabel("\u25cf")
        self.dot.setStyleSheet(f"color: {theme.GREEN}; font-size: 8pt;")
        self.text = QLabel("BEREIT")
        self.text.setStyleSheet(f"color: {theme.MUTED}; font-size: 8.5pt; letter-spacing: 1.6px;")
        layout.addWidget(self.dot)
        layout.addWidget(self.text)
        self.set_state("idle", "BEREIT")

    def set_state(self, state: str, text: str) -> None:
        colors = {
            "idle": theme.GREEN,
            "busy": theme.ACCENT,
            "listening": theme.RED,
            "error": theme.RED,
            "transcribing": theme.BLUE,
        }
        color = colors.get(state, theme.MUTED)
        self.dot.setStyleSheet(f"color: {color}; font-size: 8pt;")
        self.text.setText(text.upper())
        self.text.setStyleSheet(f"color: {color}; font-size: 8.5pt; letter-spacing: 1.6px;")


class InAppToast(QFrame):
    """Small popup inside the app window for short error notices."""

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setObjectName("toast")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(
            f"QFrame#toast {{ background: {theme.SURFACE_2};"
            f" border: 1px solid {theme.RED}; border-radius: 3px; }}")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 16, 10)
        layout.setSpacing(12)
        self.title = QLabel("HINWEIS")
        self.title.setStyleSheet(
            f"color: {theme.RED}; font-size: 7.2pt; font-weight: 700;"
            " letter-spacing: 1.8px;")
        self.title.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.addWidget(self.title)
        self.text = QLabel("")
        self.text.setWordWrap(True)
        self.text.setStyleSheet(f"color: {theme.TEXT}; font-size: 9pt;")
        layout.addWidget(self.text, 1)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide)
        self.hide()

    def show_message(self, title: str, message: str, timeout_ms: int = 4200) -> None:
        self.title.setText(title.upper())
        self.text.setText(message)
        self.text.setFixedWidth(400)
        self.text.adjustSize()
        height = max(58, self.text.sizeHint().height() + 24)
        width = 14 + 16 + 12 + self.title.sizeHint().width() + 400
        self.setFixedSize(width, height)
        self._place()
        self.show()
        self.raise_()
        self._timer.start(timeout_ms)

    def _place(self) -> None:
        parent = self.parentWidget()
        if parent is None:
            return
        x = max(12, (parent.width() - self.width()) // 2)
        y = max(12, parent.height() - self.height() - 48)
        self.move(x, y)


class VoiceOverlay(QWidget):
    """Small always-on-top confirmation shown while the game has focus."""

    def __init__(self):
        super().__init__(None, Qt.WindowType.FramelessWindowHint
                         | Qt.WindowType.WindowStaysOnTopHint
                         | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setFixedHeight(112)
        self.setMinimumWidth(360)

        self.panel = QFrame(self)
        self.panel.setObjectName("overlayPanel")
        self.panel.setStyleSheet(
            f"QFrame#overlayPanel {{ background: rgba(12, 14, 9, 235);"
            f"border: 1px solid {theme.ACCENT_DARK}; border-radius: 4px; }}"
        )
        layout = QHBoxLayout(self.panel)
        layout.setContentsMargins(16, 12, 20, 12)
        layout.setSpacing(14)
        self.icon = QLabel()
        self.icon.setFixedSize(64, 64)
        layout.addWidget(self.icon)
        text_box = QVBoxLayout()
        text_box.setSpacing(2)
        self.kicker = QLabel("SPRACHBEFEHL")
        self.kicker.setObjectName("kicker")
        self.name = QLabel("")
        self.name.setStyleSheet(f"color: {theme.TEXT}; font-size: 13pt; font-weight: 600;")
        self.detail = QLabel("")
        self.detail.setStyleSheet(f"color: {theme.MUTED}; font-size: 9pt;")
        text_box.addWidget(self.kicker)
        text_box.addWidget(self.name)
        text_box.addWidget(self.detail)
        layout.addLayout(text_box, 1)
        self.code = CodeStrip("", chip=22, gap=4)
        layout.addWidget(self.code, 0, Qt.AlignmentFlag.AlignVCenter)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self.panel)

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.fade_out)
        self._anim = QPropertyAnimation(self, b"windowOpacity", self)
        self._anim.setDuration(160)
        self._anim.finished.connect(self._on_anim_done)

    def show_stratagem(self, stratagem: Stratagem, detail: str, timeout_ms: int = 2600) -> None:
        self.icon.setPixmap(icon_pixmap(stratagem.icon, 60))
        self.name.setText(stratagem.name)
        self.detail.setText(detail)
        self.code.set_code(stratagem.code, category_color(stratagem.category))
        self.kicker.setText("SPRACHBEFEHL")
        self._present(timeout_ms)

    def show_text(self, title: str, text: str, detail: str = "", timeout_ms: int = 2000) -> None:
        self.icon.setPixmap(QPixmap())
        self.kicker.setText(title)
        self.name.setText(text)
        self.detail.setText(detail)
        self.code.set_code("")
        self._present(timeout_ms)

    def _present(self, timeout_ms: int) -> None:
        self.adjustSize()
        screen = QGuiApplication.primaryScreen()
        if screen is not None:
            rect = screen.availableGeometry()
            x = rect.center().x() - self.width() // 2
            y = rect.bottom() - self.height() - 90
            self.move(QPoint(x, y))
        self.setWindowOpacity(0.0)
        self.show()
        self.raise_()
        self._anim.stop()
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.start()
        self._timer.start(timeout_ms)

    def fade_out(self) -> None:
        self._anim.stop()
        self._anim.setStartValue(self.windowOpacity())
        self._anim.setEndValue(0.0)
        self._anim.start()

    def _on_anim_done(self) -> None:
        if self.windowOpacity() <= 0.01:
            self.hide()


def hline() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setStyleSheet(f"color: {theme.BORDER}; background: {theme.BORDER}; max-height: 1px;")
    return line


def section_label(text: str) -> QLabel:
    label = QLabel(text.upper())
    label.setObjectName("kicker")
    return label


def size_hint(width: int, height: int) -> QSize:
    return QSize(width, height)
