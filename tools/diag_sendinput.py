"""Raw SendInput probe: does GetAsyncKeyState see our injected keys?"""

from __future__ import annotations

import ctypes
import time

from app.core import input_sender as ins
from app.core.hotkeys import _is_down

print("sizeof INPUT:", ctypes.sizeof(ins._INPUT))
print("sizeof KEYBDINPUT:", ctypes.sizeof(ins._KEYBDINPUT))
print("sizeof MOUSEINPUT:", ctypes.sizeof(ins._MOUSEINPUT))

sender = ins.MacroSender()
print("f1 down ->", end=" ")
sender.key("f1", True)
seen = []
for _ in range(12):
    seen.append(_is_down(0x70))
    time.sleep(0.02)
print(seen)
sender.key("f1", False)
time.sleep(0.1)
print("after up:", _is_down(0x70))

# raw ctypes check of SendInput return value
user32 = ctypes.windll.user32
print("SendInput test:")
print("  foreground window:", user32.GetForegroundWindow())
print("  our pid:", ctypes.windll.kernel32.GetCurrentProcessId())
