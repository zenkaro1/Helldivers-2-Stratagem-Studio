import ctypes
import sys
from ctypes import wintypes

kernel32 = ctypes.windll.kernel32
advapi = ctypes.windll.advapi32

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
TOKEN_QUERY = 0x0008
TokenElevation = 20


def is_elevated_pid(pid: int) -> bool | None:
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        print(f"pid {pid}: OpenProcess failed ({ctypes.get_last_error()})")
        return None
    try:
        token = wintypes.HANDLE()
        if not advapi.OpenProcessToken(handle, TOKEN_QUERY, ctypes.byref(token)):
            print(f"pid {pid}: OpenProcessToken failed")
            return None
        try:
            elevation = wintypes.DWORD()
            size = wintypes.DWORD(ctypes.sizeof(elevation))
            ok = advapi.GetTokenInformation(token, TokenElevation,
                                            ctypes.byref(elevation), size,
                                            ctypes.byref(size))
            if not ok:
                return None
            return bool(elevation.value)
        finally:
            kernel32.CloseHandle(token)
    finally:
        kernel32.CloseHandle(handle)


def self_elevated() -> bool:
    return bool(is_elevated_pid(kernel32.GetCurrentProcess()))


print("self elevated:", self_elevated())


def pids(name: str) -> list[int]:
    import subprocess

    out = subprocess.run(["tasklist", "/FI", f"IMAGENAME eq {name}", "/FO", "CSV"],
                         capture_output=True, text=True)
    result = []
    for line in out.stdout.splitlines()[1:]:
        parts = [part.strip('"') for part in line.split('","')]
        if len(parts) >= 2 and parts[0].lower() == name.lower():
            result.append(int(parts[1]))
    return result


for process_name in ("helldivers2.exe", "StratagemStudio.exe", "steam.exe"):
    for pid in pids(process_name):
        print(f"{process_name} ({pid}) elevated: {is_elevated_pid(pid)}")
