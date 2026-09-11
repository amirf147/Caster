from dragonfly import Window, Key
from ctypes import windll

from castervoice.lib import printer

# https://github.com/mirober/pyvda
try:
    from pyvda import VirtualDesktop, AppView, get_virtual_desktops  # pylint: disable=import-error
except Exception as e:
    # This could fail on linux or windows <10
    print("Importing package pyvda failed with exception %s" % str(e))

ASFW_ANY = -1

def go_to_desktop_number(n):
    # Helps make sure that the target desktop gets focus
    windll.user32.AllowSetForegroundWindow(ASFW_ANY)
    VirtualDesktop(n).go()

def move_current_window_to_desktop(n=1, follow=False):
    hwnd = Window.get_foreground().handle
    AppView(hwnd).move(VirtualDesktop(n))
    if follow:
        go_to_desktop_number(n)

def close_all_workspaces():
    desktops = get_virtual_desktops()
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
            AppView(window.handle).pin()
            printer.out("Window pinned to all workspaces")
    except Exception as e:
        printer.out("Failed to pin window: %s" % str(e))


def unpin_current_window():
    try:
        window = Window.get_foreground()
        if window and window.handle:
            AppView(window.handle).unpin()
            printer.out("Window unpinned from all workspaces")
    except Exception as e:
        printer.out("Failed to unpin window: %s" % str(e))


def toggle_pin_current_window():
    try:
        window = Window.get_foreground()
        if window and window.handle:
            view = AppView(window.handle)
            if view.is_pinned():
                view.unpin()
                printer.out("Window unpinned from all workspaces")
            else:
                view.pin()
                printer.out("Window pinned to all workspaces")
    except Exception as e:
        printer.out("Failed to toggle pin window: %s" % str(e))


def pin_current_app():
    try:
        window = Window.get_foreground()
        if window and window.handle:
            AppView(window.handle).pin_app()
            printer.out("App pinned to all workspaces")
    except Exception as e:
        printer.out("Failed to pin app: %s" % str(e))


def unpin_current_app():
    try:
        window = Window.get_foreground()
        if window and window.handle:
            AppView(window.handle).unpin_app()
            printer.out("App unpinned from all workspaces")
    except Exception as e:
        printer.out("Failed to unpin app: %s" % str(e))


def toggle_pin_current_app():
    try:
        window = Window.get_foreground()
        if window and window.handle:
            view = AppView(window.handle)
            if view.is_app_pinned():
                view.unpin_app()
                printer.out("App unpinned from all workspaces")
            else:
                view.pin_app()
                printer.out("App pinned to all workspaces")
    except Exception as e:
        printer.out("Failed to toggle pin app: %s" % str(e))
