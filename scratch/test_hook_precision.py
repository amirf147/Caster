"""
Test precise SetWinEventHook with EVENT_SYSTEM_FOREGROUND and OBJID_WINDOW namechange.
"""

import sys
import ctypes
from ctypes import wintypes
import time

EVENT_SYSTEM_FOREGROUND = 0x0003
EVENT_OBJECT_NAMECHANGE = 0x800C
OBJID_WINDOW = 0
WINEVENT_OUTOFCONTEXT = 0x0000
WINEVENT_SKIPOWNPROCESS = 0x0002

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

WINEVENTPROC = ctypes.WINFUNCTYPE(
    None,
    wintypes.HANDLE,
    wintypes.DWORD,
    wintypes.HWND,
    wintypes.LONG,
    wintypes.LONG,
    wintypes.DWORD,
    wintypes.DWORD
)


def callback(hWinEventHook, event, hwnd, idObject, idChild, dwEventThread, dwmsEventTime):
    # Only process window-level events
    if idObject != OBJID_WINDOW and event != EVENT_SYSTEM_FOREGROUND:
        return
    print("Event 0x%04X fired for HWND %s (idObject=%s)" % (event, hwnd, idObject))


cb = WINEVENTPROC(callback)
hook_fg = user32.SetWinEventHook(
    EVENT_SYSTEM_FOREGROUND,
    EVENT_SYSTEM_FOREGROUND,
    0,
    cb,
    0,
    0,
    WINEVENT_OUTOFCONTEXT | WINEVENT_SKIPOWNPROCESS
)

hook_name = user32.SetWinEventHook(
    EVENT_OBJECT_NAMECHANGE,
    EVENT_OBJECT_NAMECHANGE,
    0,
    cb,
    0,
    0,
    WINEVENT_OUTOFCONTEXT | WINEVENT_SKIPOWNPROCESS
)

print("Hook installed cleanly: fg=%s, name=%s" % (bool(hook_fg), bool(hook_name)))
if hook_fg:
    user32.UnhookWinEvent(hook_fg)
if hook_name:
    user32.UnhookWinEvent(hook_name)
