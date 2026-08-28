"""
Modular Window Focus Tracking Subsystem.
Provides targeted, event-driven, zero-polling OS foreground window detection.
Engineered with abstract base class for cross-platform extensibility (Windows, macOS, Linux).
Compatible with Python 2.7 and Python 3.x.
"""

import sys
import threading
import time
import logging
from abc import ABCMeta, abstractmethod

_logger = logging.getLogger("caster.hud.window_tracker")


# Python 2 and 3 compatible ABC
ABC = ABCMeta("ABC", (object,), {})

# Background daemons, transient shell overlays, and system utilities to exclude from focus tracking
IGNORED_PROCESS_NAMES = frozenset([
    "adce.daemon",
    "adce",
    "adce.monitor",
    "adce.spikes",
    "shellexperiencehost",
    "startmenuexperiencehost",
    "textinputhost",
    "screencaptureui",
    "python",
    "pythonw",
])

IGNORED_WINDOW_TITLES = frozenset([
    "task switching",
    "task view",
    "snap assist",
    "cortana",
    "search",
    "start",
    "caster hud",
    "caster hud context menu",
    "caster",
    "adce daemon",
    "adce",
])


class IFocusTracker(ABC):
    """
    Abstract interface for OS-level window focus and title tracking.
    Enables pluggable implementations across Win32, macOS, Linux, and mock environments.
    """

    @abstractmethod
    def start(self):
        """Starts background event loop / listener."""
        pass

    @abstractmethod
    def stop(self):
        """Stops background event loop / listener."""
        pass

    @abstractmethod
    def get_foreground_info(self):
        """
        Returns a tuple of (process_name: str, window_title: str).
        """
        pass


class NullWindowFocusTracker(IFocusTracker):
    """Fallback focus tracker for unsupported platforms or headless testing."""

    def __init__(self, on_focus_changed=None):
        self._on_focus_changed = on_focus_changed

    def start(self):
        pass

    def stop(self):
        pass

    def get_foreground_info(self):
        return "", ""


class Win32WindowFocusTracker(IFocusTracker):
    """
    Targeted Win32 event-driven window focus tracker using SetWinEventHook.
    Listens specifically to EVENT_SYSTEM_FOREGROUND and top-level OBJID_WINDOW name changes.
    Consumes 0.00% CPU when idle by sleeping in the Windows message pump.
    """

    EVENT_SYSTEM_FOREGROUND = 0x0003
    EVENT_OBJECT_NAMECHANGE = 0x800C
    OBJID_WINDOW = 0
    WINEVENT_OUTOFCONTEXT = 0x0000
    WINEVENT_SKIPOWNPROCESS = 0x0002
    WM_QUIT = 0x0012
    GA_ROOT = 2

    def __init__(self, on_focus_changed=None):
        self._on_focus_changed = on_focus_changed
        self._thread = None
        self._thread_id = 0
        self._running = False
        self._lock = threading.Lock()
        self._hook_fg = None
        self._hook_name = None

        self._last_hwnd = 0
        self._last_process = ""
        self._last_title = ""

    def start(self):
        """Starts background Win32 message loop thread."""
        with self._lock:
            if self._running:
                return
            self._running = True
            self._thread = threading.Thread(
                target=self._worker_loop,
                name="Win32-Focus-Hook",
            )
            self._thread.daemon = True
            self._thread.start()

    def stop(self):
        """Stops the hook and posts WM_QUIT to unblock message pump."""
        with self._lock:
            if not self._running:
                return
            self._running = False
            if self._thread_id and sys.platform == "win32":
                try:
                    import ctypes
                    ctypes.windll.user32.PostThreadMessageW(self._thread_id, self.WM_QUIT, 0, 0)
                except Exception:
                    pass

    def get_foreground_info(self):
        """Returns the last known foreground (process_name, window_title)."""
        if not self._last_process and sys.platform == "win32":
            proc, title, hwnd = self._query_current_foreground()
            if proc or title:
                self._last_process = proc
                self._last_title = title
                self._last_hwnd = hwnd
        return self._last_process, self._last_title

    def _query_hwnd_info(self, hwnd):
        """Resolves process name, window title, and root HWND for a given window handle."""
        if not hwnd:
            return "", "", 0
        try:
            import ctypes
            from ctypes import wintypes
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32

            # Find top-level root window ancestor
            root = user32.GetAncestor(hwnd, self.GA_ROOT)
            target = root if root else hwnd

            # Window Title
            length = user32.GetWindowTextLengthW(target)
            title = ""
            if length > 0:
                buf = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(target, buf, length + 1)
                title = buf.value

            # Check transient titles (e.g. Alt+Tab "Task Switching")
            title_clean = title.lower().strip()
            if title_clean in IGNORED_WINDOW_TITLES:
                return "", "", 0

            # Process ID & Name
            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(target, ctypes.byref(pid))
            if not pid.value:
                return "", "", 0

            # Ignore own process (Caster HUD)
            own_pid = kernel32.GetCurrentProcessId()
            if pid.value == own_pid:
                return "", "", 0

            h_proc = kernel32.OpenProcess(0x1000, False, pid.value)  # PROCESS_QUERY_LIMITED_INFORMATION
            process_name = ""
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

            proc_clean = process_name.lower().strip()
            # Ignore background daemons and system overlays
            if proc_clean in IGNORED_PROCESS_NAMES:
                return "", "", 0

            return proc_clean, title, target
        except Exception as ex:
            _logger.debug("Win32 HWND query error: %s", ex)
            return "", "", 0

    def _query_current_foreground(self):
        """Queries current active foreground window directly."""
        try:
            import ctypes
            user32 = ctypes.windll.user32
            hwnd = user32.GetForegroundWindow()
            return self._query_hwnd_info(hwnd)
        except Exception:
            return "", "", 0

    def _worker_loop(self):
        """Dedicated thread running SetWinEventHook and Windows message loop."""
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32

        self._thread_id = kernel32.GetCurrentThreadId()

        WINEVENTPROC = ctypes.WINFUNCTYPE(
            None,
            wintypes.HANDLE,   # hWinEventHook
            wintypes.DWORD,    # event
            wintypes.HWND,     # hwnd
            wintypes.LONG,     # idObject
            wintypes.LONG,     # idChild
            wintypes.DWORD,    # dwEventThread
            wintypes.DWORD     # dwmsEventTime
        )

        def _hook_callback(hWinEventHook, event, hwnd, idObject, idChild, dwEventThread, dwmsEventTime):
            if not self._running:
                return

            # For NAMECHANGE events, only process top-level window title changes (ignore internal UI elements)
            if event == self.EVENT_OBJECT_NAMECHANGE and idObject != self.OBJID_WINDOW:
                return

            target = hwnd
            if not target:
                target = user32.GetForegroundWindow()
            if not target:
                return

            try:
                proc, title, root_hwnd = self._query_hwnd_info(target)
                if not proc and not title:
                    return

                # If HWND, process, or title changed, dispatch update immediately
                if root_hwnd != self._last_hwnd or proc != self._last_process or title != self._last_title:
                    self._last_hwnd = root_hwnd
                    self._last_process = proc
                    self._last_title = title

                    if self._on_focus_changed:
                        try:
                            self._on_focus_changed(proc, title, root_hwnd)
                        except TypeError:
                            self._on_focus_changed(proc, title)
                        except Exception as ex:
                            _logger.debug("Error in on_focus_changed callback: %s", ex)
            except Exception as ex:
                _logger.debug("Error in hook callback: %s", ex)

        # Hold a permanent reference to prevent garbage collection of the C callback
        self._c_callback = WINEVENTPROC(_hook_callback)

        hook_flags = self.WINEVENT_OUTOFCONTEXT | self.WINEVENT_SKIPOWNPROCESS

        # Hook 1: Foreground window switches (0x0003 only)
        self._hook_fg = user32.SetWinEventHook(
            self.EVENT_SYSTEM_FOREGROUND,
            self.EVENT_SYSTEM_FOREGROUND,
            0,
            self._c_callback,
            0,
            0,
            hook_flags,
        )

        # Hook 2: Window title changes (0x800C only)
        self._hook_name = user32.SetWinEventHook(
            self.EVENT_OBJECT_NAMECHANGE,
            self.EVENT_OBJECT_NAMECHANGE,
            0,
            self._c_callback,
            0,
            0,
            hook_flags,
        )

        if not self._hook_fg and not self._hook_name:
            _logger.warning("Failed to install SetWinEventHook.")
            return

        try:
            # Initial focus trigger
            proc, title, root_hwnd = self._query_current_foreground()
            if proc or title:
                self._last_hwnd = root_hwnd
                self._last_process = proc
                self._last_title = title
                if self._on_focus_changed:
                    try:
                        self._on_focus_changed(proc, title, root_hwnd)
                    except TypeError:
                        self._on_focus_changed(proc, title)

            # Windows Message Pump
            msg = wintypes.MSG()
            while self._running:
                res = user32.GetMessageW(ctypes.byref(msg), 0, 0, 0)
                if res <= 0:  # WM_QUIT or error
                    break
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
        finally:
            if self._hook_fg:
                user32.UnhookWinEvent(self._hook_fg)
                self._hook_fg = None
            if self._hook_name:
                user32.UnhookWinEvent(self._hook_name)
                self._hook_name = None


def create_window_focus_tracker(on_focus_changed=None):
    """
    Factory function instantiating the appropriate focus tracker for the current OS.
    """
    if sys.platform == "win32":
        return Win32WindowFocusTracker(on_focus_changed=on_focus_changed)
    return NullWindowFocusTracker(on_focus_changed=on_focus_changed)
