import ctypes
import sys
from ctypes import wintypes

sys.path.insert(0, r"C:\Projekte\Website Design\hd2-stratagem-studio")

from PySide6.QtWidgets import QApplication, QWidget  # noqa: E402

app = QApplication([])
w = QWidget()
w.setWindowTitle("hk_test")
w.hide()
hwnd = int(w.winId())
print("hwnd:", hwnd)
user32 = ctypes.windll.user32
user32.RegisterHotKey.restype = wintypes.BOOL
user32.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]

for i, vk in enumerate((0x70, 0x71, 0x72), start=1):  # F1 F2 F3
    ok = user32.RegisterHotKey(wintypes.HWND(hwnd), 0xC001 + i, 0, vk)
    err = ctypes.get_last_error()
    print("vk", hex(vk), "ok", bool(ok), "last_error", err)
    if ok:
        user32.UnregisterHotKey(wintypes.HWND(hwnd), 0xC001 + i)
