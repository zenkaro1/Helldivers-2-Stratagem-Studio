"""Report the integrity level (Medium/High) of the game and our processes."""

import ctypes
import subprocess
import sys
from ctypes import wintypes

kernel32 = ctypes.windll.kernel32
advapi = ctypes.windll.advapi32
user32 = ctypes.windll.user32

advapi.GetSidSubAuthorityCount.restype = ctypes.POINTER(ctypes.c_ubyte)
advapi.GetSidSubAuthorityCount.argtypes = [ctypes.c_void_p]
advapi.GetSidSubAuthority.restype = ctypes.POINTER(wintypes.DWORD)
advapi.GetSidSubAuthority.argtypes = [ctypes.c_void_p, wintypes.DWORD]

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
TOKEN_QUERY = 0x0008
TokenIntegrityLevel = 25
TokenElevATION = 20


class SID_AND_ATTRIBUTES(ctypes.Structure):
    _fields_ = [("Sid", ctypes.c_void_p), ("Attributes", wintypes.DWORD)]


class TOKEN_MANDATORY_LABEL(ctypes.Structure):
    _fields_ = [("Label", SID_AND_ATTRIBUTES)]


def _token_info(pid: int):
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return None, f"OpenProcess failed ({ctypes.get_last_error()})"
    token = wintypes.HANDLE()
    if not advapi.OpenProcessToken(handle, TOKEN_QUERY, ctypes.byref(token)):
        kernel32.CloseHandle(handle)
        return None, "OpenProcessToken failed"
    try:
        elevation = wintypes.DWORD()
        size = wintypes.DWORD(ctypes.sizeof(elevation))
        elevated = None
        if advapi.GetTokenInformation(token, TokenElevATION, ctypes.byref(elevation),
                                      size, ctypes.byref(size)):
            elevated = bool(elevation.value)

        needed = wintypes.DWORD(0)
        advapi.GetTokenInformation(token, TokenIntegrityLevel, None, 0,
                                   ctypes.byref(needed))
        buffer = ctypes.create_string_buffer(needed.value)
        level_name = None
        if advapi.GetTokenInformation(token, TokenIntegrityLevel, buffer, needed,
                                      ctypes.byref(needed)):
            label = ctypes.cast(buffer, ctypes.POINTER(TOKEN_MANDATORY_LABEL)).contents
            count = advapi.GetSidSubAuthorityCount(label.Label.Sid)
            if count:
                rid = advapi.GetSidSubAuthority(label.Label.Sid, count[0] - 1)[0]
                level_name = {
                    0x0000: "Untrusted",
                    0x1000: "Low",
                    0x2000: "Medium",
                    0x2100: "Medium+",
                    0x3000: "High (Admin)",
                    0x4000: "System",
                }.get(rid, hex(rid))
        return (elevated, level_name), None
    finally:
        kernel32.CloseHandle(token)
        kernel32.CloseHandle(handle)


def pids_for(name: str) -> list[int]:
    output = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         f"Get-Process -Name '{name}' -ErrorAction SilentlyContinue | "
         "Select-Object -ExpandProperty Id"],
        capture_output=True, text=True)
    return [int(line) for line in output.stdout.split() if line.strip().isdigit()]


print("self:", _token_info(kernel32.GetCurrentProcessId()))

for image in ("helldivers2", "StratagemStudio", "steam", "steamwebhelper"):
    for pid in pids_for(image):
        print(f"{image} ({pid}):", _token_info(pid))

print("foreground window:", user32.GetForegroundWindow())
