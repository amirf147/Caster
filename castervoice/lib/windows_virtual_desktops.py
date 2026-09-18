from dragonfly import Window, Key
from ctypes import windll

from castervoice.lib import printer

try:
    import winvda
except Exception as e:
    # This could fail on linux or windows <10
    print("Importing package winvda failed with exception %s" % str(e))

ASFW_ANY = -1

def go_to_desktop_number(n):
    # Helps make sure that the target desktop gets focus
    windll.user32.AllowSetForegroundWindow(ASFW_ANY)
    winvda.switch_desktop(n)

def move_current_window_to_desktop(n=1, follow=False):
    hwnd = Window.get_foreground().handle
    winvda.move_window_to_desktop(hwnd, n)
    if follow:
        go_to_desktop_number(n)

def close_all_workspaces():
    desktops = winvda.get_desktops()
    total = len(desktops)
    if total <= 1:
        printer.out("Only one desktop exists; nothing to close.")
        return
    go_to_desktop_number(total - 1)
    Key("wc-f4/10:" + str(total - 1)).execute()


def pin_current_window():
    try:
        window = Window.get_foreground()
        if window and window.handle:
            winvda.pin_window(window.handle)
            printer.out("Window pinned to all workspaces")
    except Exception as e:
        printer.out("Failed to pin window: %s" % str(e))


def unpin_current_window():
    try:
        window = Window.get_foreground()
        if window and window.handle:
            winvda.unpin_window(window.handle)
            printer.out("Window unpinned from all workspaces")
    except Exception as e:
        printer.out("Failed to unpin window: %s" % str(e))


def toggle_pin_current_window():
    try:
        window = Window.get_foreground()
        if window and window.handle:
            is_pinned = winvda.toggle_pin_window(window.handle)
            if is_pinned:
                printer.out("Window pinned to all workspaces")
            else:
                printer.out("Window unpinned from all workspaces")
    except Exception as e:
        printer.out("Failed to toggle pin window: %s" % str(e))


def pin_current_app():
    try:
        window = Window.get_foreground()
        if window and window.handle:
            winvda.pin_app(window.handle)
            printer.out("App pinned to all workspaces")
    except Exception as e:
        printer.out("Failed to pin app: %s" % str(e))


def unpin_current_app():
    try:
        window = Window.get_foreground()
        if window and window.handle:
            winvda.unpin_app(window.handle)
            printer.out("App unpinned from all workspaces")
    except Exception as e:
        printer.out("Failed to unpin app: %s" % str(e))


def toggle_pin_current_app():
    try:
        window = Window.get_foreground()
        if window and window.handle:
            is_pinned = winvda.toggle_pin_app(window.handle)
            if is_pinned:
                printer.out("App pinned to all workspaces")
            else:
                printer.out("App unpinned from all workspaces")
    except Exception as e:
        printer.out("Failed to toggle pin app: %s" % str(e))
