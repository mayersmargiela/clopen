from __future__ import annotations

import os
import subprocess
import time
from dataclasses import dataclass


class OwnershipError(RuntimeError):
    """The process started, but could not be safely assigned to our session."""


@dataclass
class ProcessRef:
    pid: int
    name: str
    path: str
    popen: subprocess.Popen | None = None
    handle: int | None = None
    owns_handle: bool = False


if os.name == "nt":
    import ctypes
    from ctypes import wintypes

    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _user32 = ctypes.WinDLL("user32", use_last_error=True)
    _shell32 = ctypes.WinDLL("shell32", use_last_error=True)

    _kernel32.CreateJobObjectW.argtypes = [wintypes.LPVOID, wintypes.LPCWSTR]
    _kernel32.CreateJobObjectW.restype = wintypes.HANDLE
    _kernel32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    _kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
    _kernel32.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
    _kernel32.TerminateJobObject.restype = wintypes.BOOL
    _kernel32.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
    _kernel32.TerminateProcess.restype = wintypes.BOOL
    _kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    _kernel32.CloseHandle.restype = wintypes.BOOL

    _WM_CLOSE = 0x0010

    class _ShellExecuteInfo(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.DWORD),
            ("fMask", wintypes.ULONG),
            ("hwnd", wintypes.HWND),
            ("lpVerb", wintypes.LPCWSTR),
            ("lpFile", wintypes.LPCWSTR),
            ("lpParameters", wintypes.LPCWSTR),
            ("lpDirectory", wintypes.LPCWSTR),
            ("nShow", ctypes.c_int),
            ("hInstApp", wintypes.HINSTANCE),
            ("lpIDList", wintypes.LPVOID),
            ("lpClass", wintypes.LPCWSTR),
            ("hkeyClass", wintypes.HKEY),
            ("dwHotKey", wintypes.DWORD),
            ("hIcon", wintypes.HANDLE),
            ("hProcess", wintypes.HANDLE),
        ]

    _shell32.ShellExecuteExW.argtypes = [ctypes.POINTER(_ShellExecuteInfo)]
    _shell32.ShellExecuteExW.restype = wintypes.BOOL
    _kernel32.GetProcessId.argtypes = [wintypes.HANDLE]
    _kernel32.GetProcessId.restype = wintypes.DWORD
    _kernel32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    _kernel32.GetExitCodeProcess.restype = wintypes.BOOL
    _user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    _user32.GetWindowThreadProcessId.restype = wintypes.DWORD
    _user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    _user32.PostMessageW.restype = wintypes.BOOL

    def _win_error(prefix: str) -> OSError:
        return OSError(ctypes.get_last_error(), prefix)

    def terminate_handle(handle: int, exit_code: int = 1) -> None:
        """Terminate a process handle that has not been registered yet."""
        if not _kernel32.TerminateProcess(wintypes.HANDLE(handle), exit_code):
            raise _win_error("无法回收未登记的进程")

    def launch_elevated(path: str, parameters: str, working_dir: str | None) -> tuple[int, int]:
        """Start a UAC-elevated process and return (process_handle, pid)."""
        info = _ShellExecuteInfo()
        info.cbSize = ctypes.sizeof(info)
        info.fMask = 0x00000040  # SEE_MASK_NOCLOSEPROCESS
        info.lpVerb = "runas"
        info.lpFile = path
        info.lpParameters = parameters or None
        info.lpDirectory = working_dir or None
        info.nShow = 1
        if not _shell32.ShellExecuteExW(ctypes.byref(info)):
            raise _win_error(f"管理员启动失败：{path}")
        if not info.hProcess:
            raise OwnershipError(f"管理员启动未返回进程句柄：{path}")
        pid = int(_kernel32.GetProcessId(info.hProcess))
        return int(info.hProcess), pid

    def _process_is_alive(handle: int) -> bool:
        exit_code = wintypes.DWORD()
        if not _kernel32.GetExitCodeProcess(wintypes.HANDLE(handle), ctypes.byref(exit_code)):
            return False
        return int(exit_code.value) == 259  # STILL_ACTIVE

    def _request_window_close(refs: list[ProcessRef]) -> None:
        # A PID alone is not a stable identity. Keep the process handle and
        # only post WM_CLOSE while that exact process object is still alive.
        handles_by_pid: dict[int, int] = {}
        for ref in refs:
            handle = ref.handle
            if handle is None and ref.popen is not None:
                handle = ref.popen._handle
            if handle is None or not _process_is_alive(handle):
                continue
            current_pid = int(_kernel32.GetProcessId(wintypes.HANDLE(handle)))
            if current_pid == ref.pid:
                handles_by_pid[current_pid] = handle
        if not handles_by_pid:
            return

        callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        _user32.EnumWindows.argtypes = [callback_type, wintypes.LPARAM]
        _user32.EnumWindows.restype = wintypes.BOOL

        @callback_type
        def callback(hwnd, _lparam):
            pid = wintypes.DWORD()
            _user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            handle = handles_by_pid.get(int(pid.value))
            if handle is not None and _process_is_alive(handle):
                _user32.PostMessageW(hwnd, _WM_CLOSE, 0, 0)
            return True

        _user32.EnumWindows(callback, 0)

    class ProcessGroup:
        """Own processes for one launch session using a Windows Job Object."""

        def __init__(self, label: str):
            self.label = label
            self._job = _kernel32.CreateJobObjectW(None, None)
            if not self._job:
                raise _win_error("无法创建 Windows Job Object")
            self._refs: list[ProcessRef] = []
            self._closed = False

        @property
        def has_processes(self) -> bool:
            return bool(self._refs)

        @property
        def pids(self) -> set[int]:
            return {ref.pid for ref in self._refs}

        def add_handle(
            self,
            handle: int,
            pid: int,
            name: str,
            path: str,
            popen=None,
            own_handle: bool = False,
        ) -> None:
            if self._closed:
                raise OwnershipError("进程会话已经关闭")
            ok = _kernel32.AssignProcessToJobObject(self._job, wintypes.HANDLE(handle))
            if not ok:
                raise _win_error(f"无法接管进程：{name}")
            self._refs.append(
                ProcessRef(
                    pid=pid,
                    name=name,
                    path=path,
                    popen=popen,
                    handle=handle if own_handle else None,
                    owns_handle=own_handle,
                )
            )

        def _close_owned_handles(self) -> None:
            for ref in self._refs:
                if ref.owns_handle and ref.handle is not None:
                    _kernel32.CloseHandle(wintypes.HANDLE(ref.handle))
                    ref.handle = None

        def close(self, grace_period: float = 1.5) -> int:
            if self._closed:
                return 0
            _request_window_close(self._refs)
            if grace_period > 0:
                time.sleep(grace_period)
            count = len(self._refs)
            if not _kernel32.TerminateJobObject(self._job, 1):
                raise _win_error(f"关闭进程会话失败：{self.label}")
            self._close_owned_handles()
            self._closed = True
            _kernel32.CloseHandle(self._job)
            return count

        def detach(self) -> None:
            if not self._closed:
                self._close_owned_handles()
                _kernel32.CloseHandle(self._job)
                self._closed = True

else:

    def launch_elevated(path: str, parameters: str, working_dir: str | None) -> tuple[int, int]:
        raise OwnershipError("管理员启动只支持 Windows")

    def terminate_handle(handle: int, exit_code: int = 1) -> None:
        raise OwnershipError("非 Windows 环境不支持按句柄回收进程")

    class ProcessGroup:
        """Portable fallback used for tests and non-Windows development."""

        def __init__(self, label: str):
            self.label = label
            self._refs: list[ProcessRef] = []
            self._closed = False

        @property
        def has_processes(self) -> bool:
            return bool(self._refs)

        @property
        def pids(self) -> set[int]:
            return {ref.pid for ref in self._refs}

        def add_handle(
            self,
            handle: int,
            pid: int,
            name: str,
            path: str,
            popen=None,
            own_handle: bool = False,
        ) -> None:
            if popen is None:
                raise OwnershipError("非 Windows 环境不支持接管外部进程")
            self._refs.append(ProcessRef(pid=pid, name=name, path=path, popen=popen))

        def close(self, grace_period: float = 0.2) -> int:
            count = 0
            for ref in self._refs:
                if ref.popen and ref.popen.poll() is None:
                    ref.popen.terminate()
                    try:
                        ref.popen.wait(timeout=grace_period)
                    except subprocess.TimeoutExpired:
                        ref.popen.kill()
                    count += 1
            self._closed = True
            return count

        def detach(self) -> None:
            self._closed = True
