"""Visual language: colours, fonts and the global stylesheet."""

from __future__ import annotations

import os

from PySide6.QtGui import QColor, QFont, QFontDatabase

BG = "#0a0b08"
BG_GRADIENT_TOP = "#0d0f0a"
SURFACE = "#12140f"
SURFACE_2 = "#181b13"
SURFACE_3 = "#1f2318"
BORDER = "#2b2f22"
BORDER_LIGHT = "#3d4231"
TEXT = "#eae8dd"
MUTED = "#8f9484"
DIM = "#5e6253"
ACCENT = "#f5d13f"
ACCENT_DARK = "#c9a92b"
RED = "#e2544a"
GREEN = "#9cc75f"
BLUE = "#59a9d6"

DISPLAY_FONTS = ["Bahnschrift SemiCondensed", "Bahnschrift", "Barlow Condensed", "Segoe UI"]
BODY_FONTS = ["Bahnschrift", "Segoe UI"]


def _pick_font(candidates: list[str]) -> str:
    families = set(QFontDatabase.families())
    for name in candidates:
        if name in families:
            return name
    return "Segoe UI"


def ensure_system_fonts() -> None:
    """Qt's offscreen platform starts without a font database on Windows.

    Registering the usual system fonts keeps screenshots and headless runs
    (and unusual deployments) from rendering every glyph as a box.
    """
    if QFontDatabase.families():
        return
    fonts_dir = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
    for name in ("segoeui.ttf", "seguisb.ttf", "segoeuib.ttf", "bahnschrift.ttf",
                 "consola.ttf", "consolab.ttf"):
        path = os.path.join(fonts_dir, name)
        if os.path.exists(path):
            QFontDatabase.addApplicationFont(path)


def display_font(size: int = 11, weight: QFont.Weight = QFont.Weight.DemiBold) -> QFont:
    font = QFont()
    font.setFamilies([_pick_font(DISPLAY_FONTS), "Segoe UI", "Segoe UI Symbol"])
    font.setPointSize(size)
    font.setWeight(weight)
    font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.6)
    return font


def body_font(size: int = 10) -> QFont:
    font = QFont()
    font.setFamilies([_pick_font(BODY_FONTS), "Segoe UI", "Segoe UI Symbol"])
    font.setPointSize(size)
    return font


def alpha(color: str, opacity: float) -> QColor:
    c = QColor(color)
    c.setAlphaF(max(0.0, min(1.0, opacity)))
    return c


STYLESHEET = f"""
* {{
    outline: none;
}}
QWidget {{
    background: transparent;
    color: {TEXT};
    font-size: 10pt;
}}
QMainWindow, QDialog {{
    background: {BG};
}}
QWidget#root {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 {BG_GRADIENT_TOP}, stop:1 {BG});
}}
QFrame#card {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 3px;
}}
QFrame#cardAlt {{
    background: {SURFACE_2};
    border: 1px solid {BORDER};
    border-radius: 3px;
}}
QFrame#slotCard {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 3px;
}}
QFrame#slotCard:hover {{
    border-color: {BORDER_LIGHT};
    background: {SURFACE_2};
}}
QFrame#slotCard[filled="true"]:hover {{
    border-color: {ACCENT_DARK};
}}
QFrame#slotCard[empty="true"] {{
    border: 1px dashed {BORDER_LIGHT};
    background: rgba(18, 20, 15, 0.55);
}}
QFrame#slotCard[empty="true"]:hover {{
    border-color: {ACCENT_DARK};
    background: rgba(245, 209, 63, 0.04);
}}
QLabel#kicker {{
    color: {ACCENT};
    font-size: 8.5pt;
    font-weight: 600;
    letter-spacing: 2.4px;
}}
QLabel#pageTitle {{
    color: {TEXT};
    font-size: 20pt;
    font-weight: 600;
    letter-spacing: 1.2px;
}}
QLabel#cardTitle {{
    color: {TEXT};
    font-size: 11.5pt;
    font-weight: 600;
}}
QLabel#muted {{
    color: {MUTED};
}}
QLabel#mono {{
    color: {MUTED};
    font-family: "Cascadia Mono", "Consolas";
    font-size: 9pt;
}}
QLabel#hotkeyBadge {{
    color: {ACCENT};
    background: rgba(245, 209, 63, 0.10);
    border: 1px solid rgba(245, 209, 63, 0.35);
    border-radius: 2px;
    padding: 2px 7px;
    font-size: 9pt;
    font-weight: 600;
    letter-spacing: 1px;
}}
QLabel#count {{
    color: {MUTED};
    font-size: 8.5pt;
    letter-spacing: 1.5px;
}}
QPushButton {{
    background: {SURFACE_2};
    border: 1px solid {BORDER};
    border-radius: 2px;
    padding: 7px 16px;
    color: {TEXT};
    font-size: 9pt;
    font-weight: 600;
    letter-spacing: 1.4px;
}}
QPushButton:hover {{
    border-color: {BORDER_LIGHT};
    background: {SURFACE_3};
}}
QPushButton:pressed {{
    background: #0f1109;
}}
QPushButton:disabled {{
    color: #565a4c;
    border-color: #23261c;
}}
QPushButton#primary {{
    background: {ACCENT};
    color: #14150a;
    border: 1px solid {ACCENT};
}}
QPushButton#primary:hover {{
    background: #ffe066;
    border-color: #ffe066;
}}
QPushButton#ghost {{
    background: transparent;
    border: 1px solid {BORDER};
    color: {MUTED};
}}
QPushButton#ghost:hover {{
    color: {TEXT};
    border-color: {BORDER_LIGHT};
}}
QPushButton#danger {{
    background: transparent;
    border: 1px solid #4a2a26;
    color: {RED};
    padding: 6px 10px;
}}
QPushButton#danger:hover {{
    background: #2a1512;
    border-color: {RED};
    color: #ff8b80;
}}
QPushButton#nav {{
    background: transparent;
    border: none;
    border-left: 3px solid transparent;
    padding: 10px 14px;
    text-align: left;
    color: {MUTED};
    font-size: 9.5pt;
    letter-spacing: 2px;
}}
QPushButton#nav:hover {{
    color: {TEXT};
    background: rgba(255, 255, 255, 0.02);
}}
QPushButton#nav:checked {{
    color: {ACCENT};
    border-left: 3px solid {ACCENT};
    background: rgba(245, 209, 63, 0.05);
}}
QPushButton#hotkeyEdit {{
    background: {SURFACE_2};
    border: 1px solid {BORDER};
    color: {TEXT};
    font-family: "Cascadia Mono", "Consolas";
    font-size: 9pt;
    padding: 5px 12px;
}}
QPushButton#hotkeyEdit:hover {{
    border-color: {ACCENT_DARK};
}}
QPushButton#hotkeyEdit[capturing="true"] {{
    border-color: {ACCENT};
    color: {ACCENT};
}}
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
    background: #0e100b;
    border: 1px solid {BORDER};
    border-radius: 2px;
    padding: 6px 9px;
    color: {TEXT};
    selection-background-color: {ACCENT_DARK};
    selection-color: #14150a;
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
    border-color: {ACCENT_DARK};
}}
QLineEdit#search {{
    padding: 10px 12px;
    font-size: 10.5pt;
}}
QComboBox::drop-down {{
    border: none;
    width: 18px;
}}
QComboBox::down-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {MUTED};
    margin-right: 6px;
}}
QComboBox QAbstractItemView {{
    background: {SURFACE_2};
    border: 1px solid {BORDER_LIGHT};
    selection-background-color: rgba(245, 209, 63, 0.18);
    selection-color: {TEXT};
    padding: 4px;
}}
QSpinBox {{
    padding-right: 24px;
}}
QSpinBox::up-button {{
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 20px;
    background: {SURFACE_3};
    border-left: 1px solid {BORDER};
    border-top-right-radius: 2px;
}}
QSpinBox::down-button {{
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    width: 20px;
    background: {SURFACE_3};
    border-left: 1px solid {BORDER};
    border-bottom-right-radius: 2px;
}}
QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
    background: #2a2f20;
}}
QSpinBox::up-arrow {{
    width: 0;
    height: 0;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-bottom: 5px solid {MUTED};
}}
QSpinBox::down-arrow {{
    width: 0;
    height: 0;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {MUTED};
}}
QCheckBox {{
    color: {TEXT};
    spacing: 8px;
}}
QCheckBox::indicator {{
    width: 15px;
    height: 15px;
    border: 1px solid {BORDER_LIGHT};
    background: #0e100b;
    border-radius: 2px;
}}
QCheckBox::indicator:checked {{
    background: {ACCENT};
    border-color: {ACCENT};
}}
QSlider::groove:horizontal {{
    height: 3px;
    background: {BORDER_LIGHT};
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: {ACCENT};
    width: 12px;
    margin: -5px 0;
    border-radius: 6px;
}}
QScrollArea {{
    border: none;
}}
QScrollBar:vertical {{
    background: transparent;
    width: 9px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {BORDER_LIGHT};
    border-radius: 4px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: #555b43;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: transparent;
}}
QListWidget {{
    background: transparent;
    border: none;
    outline: none;
}}
QListWidget::item {{
    padding: 6px 8px;
    border-radius: 2px;
    color: {TEXT};
}}
QListWidget::item:hover {{
    background: {SURFACE_3};
}}
QListWidget::item:selected {{
    background: rgba(245, 209, 63, 0.14);
    color: {TEXT};
}}
QToolTip {{
    background: {SURFACE_2};
    color: {TEXT};
    border: 1px solid {BORDER_LIGHT};
    padding: 4px 6px;
}}
QMenu {{
    background: {SURFACE_2};
    border: 1px solid {BORDER_LIGHT};
    padding: 4px;
}}
QMenu::item {{
    padding: 6px 18px;
    color: {TEXT};
}}
QMenu::item:selected {{
    background: rgba(245, 209, 63, 0.16);
}}
"""
