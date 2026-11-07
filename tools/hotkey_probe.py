import ctypes
import sys
from ctypes import wintypes

sys.path.insert(0, r"C:\Projekte\Website Design\hd2-stratagem-studio")

from PySide6.QtWidgets import QApplication  # noqa: E402

app = QApplication([])

from app.core.hotkeys import WM_HOTKEY, HotkeyManager  # noqa: E402

manager = HotkeyManager()
fired: list[str] = []
manager.triggered.connect(fired.append)

errors = manager.apply({"slot1": "f1", "mission_slot1": "ctrl+f9"})
print("errors:", errors)
print("bindings:", manager.bindings)

hwnd = int(manager._window.winId())
for hotkey_id, action in list(manager._ids.items()):
    ok = ctypes.windll.user32.PostMessageW(wintypes.HWND(hwnd), WM_HOTKEY, hotkey_id, 0)
    print("post", hotkey_id, action, bool(ok))

for _ in range(5):
    app.processEvents()

print("fired:", fired)
manager.suspend(True)
hotkey_id = next(iter(manager._ids))
ctypes.windll.user32.PostMessageW(wintypes.HWND(hwnd), WM_HOTKEY, hotkey_id, 0)
for _ in range(5):
    app.processEvents()
print("fired while suspended:", fired)
manager.clear()
