"""
Diagnostic script for Win32 window focus hook and Dragonfly context matching.
"""

import sys
import ctypes
from ctypes import wintypes
import time

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

GA_ROOT = 2
GA_ROOTOWNER = 3


def get_hwnd_info(hwnd):
    if not hwnd:
        return "", ""
    root = user32.GetAncestor(hwnd, GA_ROOT)
    target = root if root else hwnd

    length = user32.GetWindowTextLengthW(target)
    buf = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(target, buf, length + 1)
    title = buf.value

    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(target, ctypes.byref(pid))
    process_name = ""
    if pid.value:
        h_proc = kernel32.OpenProcess(0x1000, False, pid.value)
        if h_proc:
            try:
                path_buf = ctypes.create_unicode_buffer(1024)
                size = wintypes.DWORD(1024)
                if kernel32.QueryFullProcessImageNameW(h_proc, 0, path_buf, ctypes.byref(size)):
                    full_path = path_buf.value
                    process_name = full_path.rsplit("\\", 1)[-1]
                    if process_name.lower().endswith(".exe"):
                        process_name = process_name[:-4]
            finally:
                kernel32.CloseHandle(h_proc)

    return process_name.lower(), title


if __name__ == "__main__":
    fg = user32.GetForegroundWindow()
    proc, title = get_hwnd_info(fg)
    print("Current Foreground HWND: %s -> Process: '%s', Title: '%s'" % (fg, proc, title))
