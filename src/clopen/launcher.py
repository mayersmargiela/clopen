from __future__ import annotations

import os
import shlex
import subprocess
import webbrowser
from pathlib import Path

from .models import AppEntry, AppGroup, CloseReport, EntryResult, LaunchReport
from .process_control import OwnershipError, ProcessGroup, launch_elevated, terminate_handle


_BROWSER_NAMES = {
    "chrome.exe",
    "firefox.exe",
    "msedge.exe",
    "brave.exe",
    "opera.exe",
    "vivaldi.exe",
    "chromium.exe",
}


def _split_arguments(value: str) -> list[str]:
    if not value.strip():
        return []
    try:
        return shlex.split(value, posix=False)
    except ValueError:
        return value.split()


def _is_browser(path: str) -> bool:
    return Path(path).name.lower() in _BROWSER_NAMES


def _stop_unregistered_process(process: subprocess.Popen) -> str:
    """Reclaim a child that failed ownership registration before it can leak."""
    try:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=0.5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=0.5)
        return ""
    except OSError as exc:
        return f"；回收未登记进程失败：{exc}"


def _open_external(entry: AppEntry) -> EntryResult:
    try:
        if entry.is_folder or entry.is_file:
            if not entry.path:
                return EntryResult(entry.name, "failed", "缺少文件或文件夹路径")
            os.startfile(os.path.expandvars(entry.path))
            if entry.url:
                webbrowser.open(entry.url)
            return EntryResult(entry.name, "unmanaged", "由系统关联程序打开，未纳入关闭会话")
        if entry.is_uwp:
            subprocess.Popen(
                ["explorer.exe", f"shell:AppsFolder\\{entry.path}"],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return EntryResult(entry.name, "unmanaged", "UWP 生命周期暂未纳入关闭会话")
        if not entry.path and entry.url:
            webbrowser.open(entry.url)
            return EntryResult(entry.name, "unmanaged", "默认浏览器打开，未纳入关闭会话")
        if entry.url and _is_browser(entry.path):
            subprocess.Popen(
                [entry.path, entry.url, *_split_arguments(entry.arguments)],
                cwd=entry.working_dir or None,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return EntryResult(entry.name, "unmanaged", "浏览器可能复用已有进程，未自动关闭")
    except OSError as exc:
        return EntryResult(entry.name, "failed", str(exc))
    return EntryResult(entry.name, "failed", "无法识别的外部启动项")


def _launch_managed(entry: AppEntry, session: ProcessGroup) -> EntryResult:
    path = os.path.expandvars(entry.path)
    if not path or not os.path.exists(path):
        return EntryResult(entry.name, "failed", f"找不到程序：{path or '(空)'}")
    args = _split_arguments(entry.arguments)
    if entry.url:
        args.append(entry.url)
    cwd = os.path.expandvars(entry.working_dir) if entry.working_dir else ""
    if cwd and not os.path.isdir(cwd):
        cwd = ""
    try:
        if entry.run_as_admin:
            parameters = subprocess.list2cmdline(args)
            handle = None
            registered = False
            try:
                handle, pid = launch_elevated(path, parameters, cwd or None)
                session.add_handle(handle, pid, entry.name, path, own_handle=True)
                registered = True
            except (OSError, OwnershipError) as exc:
                cleanup = ""
                if handle is not None:
                    try:
                        terminate_handle(handle)
                    except (OSError, OwnershipError) as cleanup_exc:
                        cleanup = f"；回收未登记进程失败：{cleanup_exc}"
                return EntryResult(
                    entry.name,
                    "failed",
                    f"启动后未能安全登记，未纳入关闭会话：{exc}{cleanup}",
                )
            finally:
                if handle is not None and not registered and os.name == "nt":
                    import ctypes

                    ctypes.windll.kernel32.CloseHandle(handle)
            return EntryResult(entry.name, "started", f"PID {pid}（管理员）")

        creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        process = subprocess.Popen(
            [path, *args],
            cwd=cwd or None,
            creationflags=creationflags,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            session.add_handle(process._handle, process.pid, entry.name, path, popen=process)
        except Exception as exc:
            cleanup = _stop_unregistered_process(process)
            return EntryResult(
                entry.name,
                "failed",
                f"启动后未能安全登记，未纳入关闭会话：{exc}{cleanup}",
            )
        return EntryResult(entry.name, "started", f"PID {process.pid}")
    except (OSError, OwnershipError) as exc:
        return EntryResult(entry.name, "failed", str(exc))


class BatchController:
    def __init__(self):
        self._sessions: dict[str, ProcessGroup] = {}

    @property
    def active_groups(self) -> set[str]:
        return set(self._sessions)

    def launch_group(self, group: AppGroup) -> LaunchReport:
        if group.name in self._sessions:
            return LaunchReport(
                group.name,
                [EntryResult(group.name, "failed", "该组合已有活动会话，请先关闭")],
            )
        report = LaunchReport(group.name)
        try:
            session = ProcessGroup(group.name)
        except Exception as exc:
            report.results.append(EntryResult(group.name, "failed", f"无法创建关闭会话：{exc}"))
            return report
        for entry in group.entries:
            if entry.is_external or (entry.url and _is_browser(entry.path)):
                report.results.append(_open_external(entry))
            else:
                report.results.append(_launch_managed(entry, session))
        if session.has_processes:
            self._sessions[group.name] = session
        else:
            session.detach()
        return report

    def close_group(self, group_name: str) -> CloseReport:
        session = self._sessions.get(group_name)
        if session is None:
            return CloseReport(group_name, 0, "没有可关闭的活动会话")
        try:
            count = session.close()
        except Exception as exc:
            return CloseReport(group_name, 0, str(exc))
        self._sessions.pop(group_name, None)
        return CloseReport(group_name, count, "已关闭本次会话登记的进程")

    def close_all(self) -> list[CloseReport]:
        return [self.close_group(name) for name in list(self._sessions)]

    def detach_all(self) -> None:
        for session in self._sessions.values():
            session.detach()
        self._sessions.clear()
