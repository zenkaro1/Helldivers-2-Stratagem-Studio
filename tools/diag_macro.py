"""Diagnose the macro chain: key polling, SendInput and focus."""

from __future__ import annotations

import sys

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QApplication, QLineEdit, QVBoxLayout, QWidget

from app.core.hotkeys import HotkeyManager, _is_down, _vk_for
from app.core.input_sender import MacroSender

app = QApplication(sys.argv)
window = QWidget()
window.setWindowTitle("MacroDiag")
layout = QVBoxLayout(window)
edit = QLineEdit()
layout.addWidget(edit)
window.resize(400, 120)
window.show()
window.activateWindow()
edit.setFocus()

fired: list[str] = []
manager = HotkeyManager()
manager.triggered.connect(lambda action: (fired.append(action), print("HOTKEY", action)))
print("apply:", manager.apply({"slot1": "f1", "slot2": "f2"}))

sender = MacroSender()


def press_f1() -> None:
    print("pressing F1, is_down before:", _is_down(_vk_for("f1")))
    sender.key("f1", True)


def release_f1() -> None:
    sender.key("f1", False)


def type_a() -> None:
    sender.key("a", True)
    sender.key("a", False)


QTimer.singleShot(600, press_f1)
QTimer.singleShot(750, release_f1)
QTimer.singleShot(900, type_a)


def finish() -> None:
    print("hotkeys fired:", fired)
    print("line edit:", repr(edit.text()))
    app.quit()


QTimer.singleShot(1800, finish)
app.exec()
