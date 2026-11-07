"""Small Windows helpers (elevation state)."""

from __future__ import annotations

import ctypes
import os
from ctypes import wintypes


class _SID_AND_ATTRIBUTES(ctypes.Structure):
    _fields_ = [("Sid", ctypes.c_void_p), ("Attributes", wintypes.DWORD)]


class _TOKEN_MANDATORY_LABEL(ctypes.Structure):
    _fields_ = [("Label", _SID_AND_ATTRIBUTES)]


def integrity_rid() -> int | None:
    """Integrity level RID of this process (0x2000 = Medium, 0x3000 = High)."""
    if os.name != "nt":
        return None
    try:
        advapi = ctypes.windll.advapi32
        kernel = ctypes.windll.kernel32
        kernel.GetCurrentProcess.restype = wintypes.HANDLE
        advapi.OpenProcessToken.argtypes = [
            wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)]
        advapi.OpenProcessToken.restype = wintypes.BOOL
        advapi.GetTokenInformation.argtypes = [
            wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD)]
        advapi.GetTokenInformation.restype = wintypes.BOOL
        advapi.GetSidSubAuthorityCount.restype = ctypes.POINTER(ctypes.c_ubyte)
        advapi.GetSidSubAuthorityCount.argtypes = [ctypes.c_void_p]
        advapi.GetSidSubAuthority.restype = ctypes.POINTER(wintypes.DWORD)
        advapi.GetSidSubAuthority.argtypes = [ctypes.c_void_p, wintypes.DWORD]
        token = wintypes.HANDLE()
        if not advapi.OpenProcessToken(kernel.GetCurrentProcess(), 0x0008,
                                       ctypes.byref(token)):
            return None
        try:
            needed = wintypes.DWORD(0)
            advapi.GetTokenInformation(token, 25, None, 0, ctypes.byref(needed))
            buffer = ctypes.create_string_buffer(needed.value)
            if not advapi.GetTokenInformation(token, 25, buffer, needed,
                                              ctypes.byref(needed)):
                return None
            label = ctypes.cast(buffer, ctypes.POINTER(_TOKEN_MANDATORY_LABEL)).contents
            count = advapi.GetSidSubAuthorityCount(label.Label.Sid)
            if not count or not count[0]:
                return None
            return int(advapi.GetSidSubAuthority(label.Label.Sid, count[0] - 1)[0])
        finally:
            kernel.CloseHandle(token)
    except Exception:  # noqa: BLE001
        return None


def is_low_integrity() -> bool:
    """True for the Low integrity level (blocks hooks/input toward normal apps)."""
    rid = integrity_rid()
    return rid is not None and rid < 0x2000


def is_elevated() -> bool:
    """True when the process runs with administrator rights."""
    if os.name != "nt":
        return False
    try:
        advapi = ctypes.windll.advapi32
        kernel = ctypes.windll.kernel32
        token = wintypes.HANDLE()
        if not advapi.OpenProcessToken(kernel.GetCurrentProcess(), 0x0008,
                                       ctypes.byref(token)):
            return False
        elevation = wintypes.DWORD()
        size = wintypes.DWORD(ctypes.sizeof(elevation))
        ok = advapi.GetTokenInformation(token, 20, ctypes.byref(elevation), size,
                                        ctypes.byref(size))
        kernel.CloseHandle(token)
        return bool(ok and elevation.value)
    except Exception:  # noqa: BLE001
        return False


def focus_window(title: str) -> bool:
    """Bring an already running window to the foreground."""
    if os.name != "nt":
        return False
    try:
        user32 = ctypes.windll.user32
        hwnd = user32.FindWindowW(None, title)
        if not hwnd:
            return False
        user32.ShowWindow(hwnd, 9)  # SW_RESTORE
        user32.SetForegroundWindow(hwnd)
        return True
    except Exception:  # noqa: BLE001
        return False
