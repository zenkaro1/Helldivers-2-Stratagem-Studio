"""Widgets for the v2 loadout design: stat cards, mission cards, kits, tabs."""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPixmap, QPolygonF
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..core.models import Stratagem, category_color, category_label
from . import theme
from .widgets import CodeStrip, icon_pixmap, HotkeyBadge


class StarLabel(QWidget):
    """Painted five-point star (the ★ glyph is missing in Bahnschrift)."""

    clicked = Signal()

    def __init__(self, size: int = 14, filled: bool = False,
                 parent: QWidget | None = None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        # A star click must not reach the row/parent (it would pick the entry).
        self.setAttribute(Qt.WidgetAttribute.WA_NoMousePropagation, True)
        self._filled = filled

    def set_filled(self, filled: bool) -> None:
        self._filled = filled
        self.update()

    def paintEvent(self, _event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        size = min(self.width(), self.height())
        center = size / 2.0
        outer = size / 2.0 - 1.0
        inner = outer * 0.45
        points = []
        for index in range(10):
            radius = outer if index % 2 == 0 else inner
            angle = -1.5707963 + index * 0.6283185
            points.append(QPointF(center + radius * math.cos(angle),
                                  center + radius * math.sin(angle)))
        polygon = QPolygonF(points)
        if self._filled:
            painter.setBrush(QColor(theme.ACCENT))
            painter.setPen(Qt.PenStyle.NoPen)
        else:
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QColor(theme.DIM))
        painter.drawPolygon(polygon)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mouseReleaseEvent(event)


def _label(text: str, size: float, color: str, spacing: float = 0,
           weight: int = 400) -> QLabel:
    label = QLabel(text)
    label.setStyleSheet(
        f"color: {color}; font-size: {size}pt; letter-spacing: {spacing}px;"
        f" font-weight: {weight};"
    )
    return label


class StatBlock(QWidget):
    def __init__(self, label: str, parent: QWidget | None = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.value = _label("—", 13, theme.TEXT, 0.4, 600)
        self.caption = _label(label, 6.8, theme.DIM, 1.6, 600)
        layout.addWidget(self.value)
        layout.addWidget(self.caption)

    def set_value(self, text: str) -> None:
        self.value.setText(text)


class ThinBar(QWidget):
    def __init__(self, color: str = theme.GREEN, parent: QWidget | None = None):
        super().__init__(parent)
        self.setFixedHeight(3)
        self._value = 1.0
        self._color = color

    def set_value(self, value: float, color: str | None = None) -> None:
        self._value = max(0.0, min(1.0, value))
        if color:
            self._color = color
        self.update()

    def paintEvent(self, _event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#0E100B"))
        if self._value > 0:
            width = int(self.width() * self._value)
            painter.fillRect(0, 0, width, self.height(), QColor(self._color))


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
        self.setMinimumSize(320, 232)
        self.setFixedHeight(232)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(6)

        top = QHBoxLayout()
        top.setSpacing(8)
        self.number = _label(f"SLOT 0{index + 1}", 7.8, theme.ACCENT, 2.0, 600)
        self.hotkey = HotkeyBadge("")
        top.addWidget(self.number)
        top.addStretch(1)
        top.addWidget(self.hotkey)
        layout.addLayout(top)

        middle = QHBoxLayout()
        middle.setSpacing(12)
        self.icon = QLabel()
        self.icon.setFixedSize(54, 54)
        self.icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        middle.addWidget(self.icon)
        text = QVBoxLayout()
        text.setSpacing(1)
        self.name = _label("Stratagem wählen", 11, theme.MUTED, 0, 600)
        self.name.setWordWrap(True)
        self.category = _label("", 7.4, theme.MUTED, 1.6, 600)
        self.traits = _label("", 6.6, theme.DIM, 1.4, 600)
        self.traits.setWordWrap(True)
        text.addWidget(self.name)
        text.addWidget(self.category)
        text.addWidget(self.traits)
        middle.addLayout(text, 1)
        layout.addLayout(middle)

        rule = QFrame()
        rule.setFixedHeight(1)
        rule.setStyleSheet(f"background: {theme.BORDER};")
        layout.addWidget(rule)

        stats = QHBoxLayout()
        stats.setSpacing(16)
        self.stat_cooldown = StatBlock("COOLDOWN")
        self.stat_uses = StatBlock("EINSÄTZE")
        self.stat_radius = StatBlock("RADIUS")
        self.stat_ap = StatBlock("PANZERUNG")
        stats.addWidget(self.stat_cooldown)
        stats.addWidget(self.stat_uses)
        stats.addWidget(self.stat_radius)
        stats.addWidget(self.stat_ap)
        stats.addStretch(1)
        layout.addLayout(stats)

        layout.addStretch(1)

        code_row = QHBoxLayout()
        code_row.setSpacing(8)
        code_caption = _label("CODE", 6.8, theme.DIM, 1.8, 600)
        code_row.addWidget(code_caption)
        self.code = CodeStrip("", chip=16, gap=4)
        code_row.addWidget(self.code)
        code_row.addStretch(1)
        layout.addLayout(code_row)

        self.bar = ThinBar(theme.GREEN)
        layout.addWidget(self.bar)

        self._stratagem: Stratagem | None = None
        self._refresh_style()

    # ------------------------------------------------------------------
    def set_stratagem(self, stratagem: Stratagem | None, hotkey: str = "",
                      cooldown: int | None = None, uses: int | None = None) -> None:
        self._stratagem = stratagem
        self.hotkey.set_key(hotkey)
        if stratagem is None:
            self.setProperty("empty", True)
            self.setProperty("filled", False)
            self.icon.setPixmap(QPixmap())
            self.icon.setText("+")
            self.icon.setStyleSheet(
                f"border: 1px dashed {theme.BORDER_LIGHT}; color: {theme.MUTED};"
                "font-size: 18pt; background: transparent;"
            )
            self.name.setText("Stratagem wählen")
            self.name.setStyleSheet(
                f"color: {theme.MUTED}; font-size: 11pt; font-weight: 600;")
            self.category.setText("")
            self.traits.setText("")
            self.code.set_code("")
            self.stat_cooldown.set_value("—")
            self.stat_uses.set_value("—")
            self.stat_radius.set_value("—")
            self.stat_ap.set_value("—")
            self.stat_radius.setVisible(False)
            self.stat_ap.setVisible(False)
            self.bar.set_value(0, theme.BORDER)
            self._refresh_style()
            return

        color = category_color(stratagem.category)
        self.setProperty("empty", False)
        self.setProperty("filled", True)
        self.icon.setStyleSheet(
            f"border: 1px solid {theme.BORDER}; background: #0C0E09;")
        self.icon.setPixmap(icon_pixmap(stratagem.icon, 50))
        self.name.setText(stratagem.name)
        self.name.setStyleSheet(
            f"color: {theme.TEXT}; font-size: 11pt; font-weight: 600;")
        self.category.setText(category_label(stratagem.category).upper())
        self.category.setStyleSheet(
            f"color: {theme.alpha(color, 0.9).name()}; font-size: 7.4pt;"
            " letter-spacing: 1.6px; font-weight: 600;")
        self.traits.setText(" · ".join(trait.upper() for trait in stratagem.traits[:3]))
        self.traits.setToolTip(" · ".join(stratagem.traits))
        self.code.set_code(stratagem.code, color)
        effective = cooldown if cooldown is not None else stratagem.cooldown
        effective_uses = uses if uses is not None else stratagem.uses
        self.stat_cooldown.set_value(f"{effective} s" if effective else "—")
        self.stat_uses.set_value(str(effective_uses) if effective_uses else "—")
        self.stat_radius.set_value(f"{stratagem.radius} m" if stratagem.radius else "—")
        self.stat_radius.setVisible(stratagem.radius is not None)
        self.stat_ap.set_value(stratagem.ap_text)
        self.stat_ap.setVisible(bool(stratagem.ap))
        if stratagem.ap:
            self.stat_ap.setToolTip(
                f"Panzerung {stratagem.ap_text} (Stufe {stratagem.ap}/10)")
        else:
            self.stat_ap.setToolTip("")
        self.bar.set_value(1.0, color)
        if stratagem.cooldown and effective and effective != stratagem.cooldown:
            self.stat_cooldown.setToolTip(
                f"Basis {stratagem.cooldown} s – mit Schiff-Upgrades {effective} s")
        else:
            self.stat_cooldown.setToolTip("")
        self._refresh_style()

    def set_progress(self, remaining: float, cooldown: int | None,
                     color: str | None = None) -> None:
        if remaining <= 0.5 or not cooldown:
            self.bar.set_value(1.0, color or theme.GREEN)
            return
        self.bar.set_value(max(0.0, 1.0 - remaining / cooldown), theme.ACCENT)

    def _refresh_style(self) -> None:
        style = self.style()
        style.unpolish(self)
        style.polish(self)
        self.update()

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton and self.rect().contains(
                event.position().toPoint()):
            self.clicked.emit(self.index)
        super().mouseReleaseEvent(event)

    def contextMenuEvent(self, event) -> None:  # noqa: N802
        if self._stratagem is not None:
            self.clear_requested.emit(self.index)
        event.accept()


class MissionCard(QFrame):
    clicked = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("cardAlt")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(92)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)
        self.icon = QLabel()
        self.icon.setFixedSize(44, 44)
        self.icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.icon)
        text = QVBoxLayout()
        text.setSpacing(1)
        self.name = _label("", 10.5, theme.TEXT, 0, 600)
        self.hotkey = _label("", 6.8, theme.ACCENT, 1.6, 600)
        self.code = CodeStrip("", chip=14, gap=3)
        text.addWidget(self.name)
        text.addWidget(self.hotkey)
        text.addWidget(self.code)
        layout.addLayout(text, 1)
        self._stratagem_id = ""

    def set_stratagem(self, stratagem: Stratagem, hotkey: str) -> None:
        self._stratagem_id = stratagem.id
        self.icon.setPixmap(icon_pixmap(stratagem.icon, 40))
        self.name.setText(stratagem.name)
        self.hotkey.setText(f"TASTE {hotkey}" if hotkey else "KLICK ZUM AUSFÜHREN")
        self.code.set_code(stratagem.code, category_color(stratagem.category))

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._stratagem_id)
        super().mouseReleaseEvent(event)


class KitCard(QFrame):
    load_requested = Signal(str)
    edit_requested = Signal(str)
    delete_requested = Signal(str)
    favorite_toggled = Signal(str)
    clicked = Signal(str)

    def __init__(self, key: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.key = key
        self.setObjectName("slotCard")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedSize(288, 216)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(6)

        top = QHBoxLayout()
        top.setSpacing(6)
        self.star = StarLabel(14)
        self.star.clicked.connect(lambda: self.favorite_toggled.emit(self.key))
        self.title = _label("", 10.5, theme.TEXT, 0.8, 600)
        self.tag = _label("", 6.2, theme.ACCENT, 1.2, 600)
        self.tag.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        top.addWidget(self.star)
        top.addWidget(self.title, 1)
        top.addWidget(self.tag)
        layout.addLayout(top)

        self.when = _label("", 6.6, theme.DIM, 1.4, 600)
        layout.addWidget(self.when)

        icons = QHBoxLayout()
        icons.setSpacing(10)
        self.icons: list[QLabel] = []
        self.lines: list[QFrame] = []
        for _ in range(4):
            holder = QVBoxLayout()
            holder.setSpacing(3)
            icon = QLabel()
            icon.setFixedSize(56, 56)
            icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon.setStyleSheet(f"border: 1px solid {theme.BORDER}; background: #0C0E09;")
            line = QFrame()
            line.setFixedHeight(2)
            line.setStyleSheet(f"background: {theme.BORDER};")
            holder.addWidget(icon)
            holder.addWidget(line)
            icons.addLayout(holder)
            self.icons.append(icon)
            self.lines.append(line)
        icons.addStretch(1)
        layout.addLayout(icons)
        layout.addStretch(1)

        buttons = QHBoxLayout()
        buttons.setSpacing(6)
        self.load_btn = QPushButton("LADEN")
        self.load_btn.setObjectName("primary")
        self.load_btn.setFixedHeight(32)
        self.load_btn.clicked.connect(lambda: self.load_requested.emit(self.key))
        self.edit_btn = QPushButton("BEARBEITEN")
        self.edit_btn.setObjectName("ghost")
        self.edit_btn.setFixedHeight(30)
        self.edit_btn.clicked.connect(lambda: self.edit_requested.emit(self.key))
        self.delete_btn = QPushButton("LÖSCHEN")
        self.delete_btn.setObjectName("danger")
        self.delete_btn.setFixedHeight(30)
        self.delete_btn.setFixedWidth(88)
        self.delete_btn.setToolTip("Kit löschen")
        self.delete_btn.clicked.connect(lambda: self.delete_requested.emit(self.key))
        layout.addWidget(self.load_btn)
        buttons.addWidget(self.edit_btn, 1)
        buttons.addWidget(self.delete_btn)
        layout.addLayout(buttons)

    def set_kit(self, name: str, tag: str, icons: list[tuple[str, str, str]],
                favorite: bool, when: str) -> None:
        self.title.setText(name)
        self.tag.setText(tag.upper())
        self.when.setText(when.upper())
        self.star.set_filled(favorite)
        names = [entry[2] for entry in icons]
        self.setToolTip("\n".join(names) if names else "Leeres Kit")
        for index, icon in enumerate(self.icons):
            if index < len(icons):
                icon_name, color, _label_text = icons[index]
                icon.setPixmap(icon_pixmap(icon_name, 38))
                icon.setStyleSheet(
                    f"border: 1px solid {theme.BORDER}; background: #0C0E09;")
                icon.setToolTip(names[index])
                self.lines[index].setStyleSheet(f"background: {color};")
            else:
                icon.setPixmap(QPixmap())
                icon.setText("")
                icon.setToolTip("")
                self.lines[index].setStyleSheet(f"background: {theme.BORDER};")

    def contextMenuEvent(self, event) -> None:  # noqa: N802
        from PySide6.QtWidgets import QMenu

        menu = QMenu(self)
        delete = menu.addAction("Kit löschen")
        action = menu.exec(event.globalPos())
        if action is delete:
            self.delete_requested.emit(self.key)
        event.accept()


class SegmentedTabs(QWidget):
    changed = Signal(int)

    def __init__(self, labels: tuple[str, str], parent: QWidget | None = None):
        super().__init__(parent)
        self.setFixedHeight(34)
        self.setFixedWidth(236)
        frame = QFrame(self)
        frame.setGeometry(0, 0, 236, 34)
        frame.setStyleSheet(
            f"background: #0E100B; border: 1px solid {theme.BORDER_LIGHT};"
            " border-radius: 2px;")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(0)
        self.buttons: list[QPushButton] = []
        for index, label in enumerate(labels):
            button = QPushButton(label)
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(lambda _=False, i=index: self._select(i))
            button.setStyleSheet(self._style(False))
            layout.addWidget(button, 1)
            self.buttons.append(button)
        self._select(0)

    def _style(self, active: bool) -> str:
        if active:
            return (
                "QPushButton { background: %s; color: #14150A; border: none;"
                " border-radius: 2px; font-size: 7.5pt; font-weight: 700;"
                " letter-spacing: 1.6px; }" % theme.ACCENT)
        return ("QPushButton { background: transparent; color: %s; border: none;"
                " font-size: 7.5pt; font-weight: 600; letter-spacing: 1.6px; }"
                % theme.MUTED)

    def _select(self, index: int) -> None:
        for position, button in enumerate(self.buttons):
            button.setChecked(position == index)
            button.setStyleSheet(self._style(position == index))
        self.changed.emit(index)

    def set_active(self, index: int) -> None:
        for position, button in enumerate(self.buttons):
            button.blockSignals(True)
            button.setChecked(position == index)
            button.setStyleSheet(self._style(position == index))
            button.blockSignals(False)
