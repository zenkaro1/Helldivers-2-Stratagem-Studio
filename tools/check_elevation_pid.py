import ctypes
import sys
from ctypes import wintypes

kernel32 = ctypes.windll.kernel32
advapi = ctypes.windll.advapi32

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
TOKEN_QUERY = 0x0008
TokenElevation = 20


def elevated(pid: int) -> bool | None:
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return None
    try:
        token = wintypes.HANDLE()
        if not advapi.OpenProcessToken(handle, TOKEN_QUERY, ctypes.byref(token)):
            return None
        try:
            value = wintypes.DWORD()
            size = wintypes.DWORD(ctypes.sizeof(value))
            if not advapi.GetTokenInformation(token, TokenElevation,
                                              ctypes.byref(value), size,
                                              ctypes.byref(size)):
                return None
            return bool(value.value)
        finally:
            kernel32.CloseHandle(token)
    finally:
        kernel32.CloseHandle(handle)


for raw in sys.argv[1:]:
    pid = int(raw)
    print(pid, "->", elevated(pid))

print("self ->", elevated(kernel32.GetCurrentProcessId()))
