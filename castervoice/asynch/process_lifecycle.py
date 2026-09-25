# -*- coding: utf-8 -*-
"""
Cross-platform child process lifecycle and containment management.

Provides operating-system-specific containment strategies so background
daemon processes (such as the PyQt Heads-Up Display) are reliably terminated
when the parent Caster process exits, avoiding orphaned GUI processes across
Windows, Linux, and macOS.
"""

import os
import signal
import subprocess
import sys


class BaseProcessStrategy(object):
    """Base interface for platform-specific child process lifecycle management."""

    def get_popen_kwargs(self):
        """Returns additional keyword arguments to pass to subprocess.Popen."""
        return {}

    def bind_process(self, proc):
        """
        Called immediately after process spawning to bind child to parent lifecycle.
        """
        pass

    def terminate_process(self, proc):
        """Forcefully terminates the process and any associated process group."""
        if proc is None:
            return
        try:
            proc.kill()
        except Exception:
            pass


class WindowsProcessStrategy(BaseProcessStrategy):
    """
    Windows implementation using Win32 Job Objects.
    Configured with JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE so the Windows kernel
    automatically kills child processes when the parent handle is closed.
    """

    def __init__(self):
        self._job = None

    def _get_or_create_job(self):
        if self._job is not None:
            return self._job
        try:
            import ctypes
            from ctypes import wintypes
            kernel32 = ctypes.windll.kernel32
            job = kernel32.CreateJobObjectW(None, None)
            if not job:
                return None

            class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
                _fields_ = [
                    ("PerProcessUserTimeLimit", wintypes.LARGE_INTEGER),
                    ("PerJobUserTimeLimit", wintypes.LARGE_INTEGER),
                    ("LimitFlags", wintypes.DWORD),
                    ("MinimumWorkingSetSize", ctypes.c_size_t),
                    ("MaximumWorkingSetSize", ctypes.c_size_t),
                    ("ActiveProcessLimit", wintypes.DWORD),
                    ("Affinity", ctypes.c_size_t),
                    ("PriorityClass", wintypes.DWORD),
                    ("SchedulingClass", wintypes.DWORD),
                ]

            class IO_COUNTERS(ctypes.Structure):
                _fields_ = [(f, ctypes.c_uint64) for f in [
                    "ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
                    "ReadTransferCount", "WriteTransferCount", "OtherTransferCount"
                ]]

            class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
                _fields_ = [
                    ("BasicLimitInformation", JOBOBJECT_BASIC_LIMIT_INFORMATION),
                    ("IoInfo", IO_COUNTERS),
                    ("ProcessMemoryLimit", ctypes.c_size_t),
                    ("JobMemoryLimit", ctypes.c_size_t),
                    ("PeakProcessMemoryLimit", ctypes.c_size_t),
                    ("PeakJobMemoryLimit", ctypes.c_size_t),
                ]

            info = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
            info.BasicLimitInformation.LimitFlags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE

            JobObjectExtendedLimitInformation = 9
            res = kernel32.SetInformationJobObject(
                job, JobObjectExtendedLimitInformation,
                ctypes.byref(info), ctypes.sizeof(info)
            )
            if not res:
                kernel32.CloseHandle(job)
                return None
            self._job = job
            return self._job
        except Exception:
            return None

    def bind_process(self, proc):
        if proc is None:
            return
        try:
            job = self._get_or_create_job()
            if job and hasattr(proc, "_handle") and proc._handle:
                import ctypes
                ctypes.windll.kernel32.AssignProcessToJobObject(job, int(proc._handle))
        except Exception:
            pass


class LinuxProcessStrategy(BaseProcessStrategy):
    """
    Linux implementation using PR_SET_PDEATHSIG.
    Instructs the Linux kernel to send SIGTERM to the child process as soon
    as the parent process terminates, matching Windows Job Object containment.
    Also starts the process in its own session/process group for clean group kills.
    """

    def get_popen_kwargs(self):
        kwargs = {}
        try:
            import ctypes
            import ctypes.util
            libc_path = ctypes.util.find_library("c")
            if libc_path:
                libc = ctypes.CDLL(libc_path, use_errno=True)
                PR_SET_PDEATHSIG = 1

                def _set_pdeathsig():
                    libc.prctl(PR_SET_PDEATHSIG, signal.SIGTERM)
                    os.setsid()

                kwargs["preexec_fn"] = _set_pdeathsig
            else:
                kwargs["start_new_session"] = True
        except Exception:
            kwargs["start_new_session"] = True
        return kwargs

    def terminate_process(self, proc):
        if proc is None:
            return
        try:
            # Kill entire process group if running in own session
            pgid = os.getpgid(proc.pid)
            os.killpg(pgid, signal.SIGKILL)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass


class DarwinProcessStrategy(BaseProcessStrategy):
    """
    macOS (Darwin) implementation.
    Starts child in a new process group to allow clean group termination.
    """

    def get_popen_kwargs(self):
        return {"start_new_session": True}

    def terminate_process(self, proc):
        if proc is None:
            return
        try:
            pgid = os.getpgid(proc.pid)
            os.killpg(pgid, signal.SIGKILL)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass


def get_process_strategy():
    """
    Factory returning the appropriate ProcessStrategy for the active operating system.
    """
    if sys.platform == "win32":
        return WindowsProcessStrategy()
    elif sys.platform.startswith("linux"):
        return LinuxProcessStrategy()
    elif sys.platform == "darwin":
        return DarwinProcessStrategy()
    return BaseProcessStrategy()
