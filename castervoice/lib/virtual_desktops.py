import sys

if sys.platform == "win32":
    from .windows_virtual_desktops import go_to_desktop_number
    from .windows_virtual_desktops import move_current_window_to_desktop
    from .windows_virtual_desktops import close_all_workspaces
    from .windows_virtual_desktops import pin_current_window
    from .windows_virtual_desktops import unpin_current_window
    from .windows_virtual_desktops import toggle_pin_current_window
    from .windows_virtual_desktops import pin_current_app
    from .windows_virtual_desktops import unpin_current_app
    from .windows_virtual_desktops import toggle_pin_current_app
else:
    from . import printer

    def _not_implemented(*args, **kwargs):
        printer.out("Virtual desktop commands are not implemented on this platform")

    def go_to_desktop_number(n):
        _not_implemented()

    def move_current_window_to_desktop(n=1, follow=False):
        _not_implemented()

    def close_all_workspaces():
        _not_implemented()

    def pin_current_window():
        _not_implemented()

    def unpin_current_window():
        _not_implemented()

    def toggle_pin_current_window():
        _not_implemented()

    def pin_current_app():
        _not_implemented()

    def unpin_current_app():
        _not_implemented()

    def toggle_pin_current_app():
        _not_implemented()
