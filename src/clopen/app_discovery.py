from __future__ import annotations

import json
import os
import re
import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path

from .models import AppEntry


# Clopen's software picker should be a launcher catalog, not an inventory of
# every executable registered on Windows. These tokens cover the common
# maintenance/helper shortcuts that users do not think of as "software".
_NON_APP_NAME_TOKENS = (
    "uninstall",
    "uninstaller",
    "installer",
    "install ",
    "setup",
    "update",
    "updater",
    "repair",
    "maintenance",
    "crash reporter",
    "crash handler",
    "helper",
    "service",
    "register",
    "registration",
    "release notes",
    "readme",
    "documentation",
    "manual",
    "website",
    "homepage",
    "卸载",
    "安装程序",
    "安装向导",
    "更新程序",
    "自动更新",
    "修复",
    "维护",
    "帮助文档",
    "使用说明",
    "用户手册",
    "发行说明",
    "官方网站",
)

_NON_APP_EXE_PATTERNS = (
    r"^unins\d*\.exe$",
    r"^uninstall(?:er)?\.exe$",
    r"^setup\.exe$",
    r"^installer\.exe$",
    r"^update(?:r)?\.exe$",
    r"^maintenancetool\.exe$",
    r"^repair\.exe$",
    r"^crashpad_handler\.exe$",
    r"^crashreporter\.exe$",
)


@dataclass(frozen=True)
class DiscoveredApp:
    name: str
    path: str = ""
    app_id: str = ""
    arguments: str = ""
    working_dir: str = ""

    @property
    def detail(self) -> str:
        if self.path:
            return self.path
        return "Windows 应用"

    def to_entry(self) -> AppEntry:
        if self.path:
            # Desktop apps default to administrator mode. Users can still
            # turn it off later in the entry editor when a program does not
            # need elevation.
            return AppEntry(
                name=self.name,
                path=self.path,
                arguments=self.arguments,
                working_dir=self.working_dir,
                run_as_admin=True,
            )
        return AppEntry(name=self.name, path=self.app_id, is_uwp=True)


def parse_executable_path(value: str) -> str:
    """Extract an executable path from registry DisplayIcon/App Paths values."""
    text = os.path.expandvars(str(value or "")).strip()
    if not text:
        return ""
    if text.startswith('"'):
        end = text.find('"', 1)
        candidate = text[1:end] if end > 1 else text.strip('"')
    else:
        match = re.match(r"^(.*?\.exe)(?:\s*,\s*-?\d+)?(?:\s+.*)?$", text, re.IGNORECASE)
        candidate = match.group(1) if match else text.split(",", 1)[0]
    candidate = candidate.strip().strip('"')
    return candidate if candidate.lower().endswith(".exe") else ""


def _looks_like_software(name: str, path: str = "") -> bool:
    """Return True for user-facing app launchers and reject helper tools."""
    clean_name = " ".join(str(name or "").split()).strip()
    if not clean_name:
        return False
    folded = clean_name.casefold()
    if any(token in folded for token in _NON_APP_NAME_TOKENS):
        return False

    if path:
        filename = Path(path).name.casefold()
        if any(re.fullmatch(pattern, filename, re.IGNORECASE) for pattern in _NON_APP_EXE_PATTERNS):
            return False
    return True


def _registry_apps() -> list[DiscoveredApp]:
    """Read Windows App Paths only.

    Deliberately do *not* read the Uninstall registry inventory. Its
    DisplayIcon values often point at uninstallers, setup helpers, services,
    SDK tools and other executable files that polluted the old software
    library. App Paths is intended for executable launchers, so it is a much
    cleaner source for Clopen.
    """
    if os.name != "nt":
        return []
    import winreg

    results: list[DiscoveredApp] = []
    app_paths = r"Software\Microsoft\Windows\CurrentVersion\App Paths"
    access_modes = (
        winreg.KEY_READ,
        winreg.KEY_READ | winreg.KEY_WOW64_64KEY,
        winreg.KEY_READ | winreg.KEY_WOW64_32KEY,
    )

    for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        for access in access_modes:
            try:
                with winreg.OpenKey(hive, app_paths, 0, access) as root:
                    for index in range(winreg.QueryInfoKey(root)[0]):
                        try:
                            key_name = winreg.EnumKey(root, index)
                            with winreg.OpenKey(root, key_name) as item:
                                path = parse_executable_path(winreg.QueryValue(item, None))
                            if path and Path(path).is_file():
                                name = Path(path).stem
                                if _looks_like_software(name, path):
                                    results.append(DiscoveredApp(name, path=path))
                        except OSError:
                            continue
            except OSError:
                pass
    return results


def _shell_apps() -> list[DiscoveredApp]:
    """Read user-facing desktop software shortcuts from the Start menu.

    The default software library intentionally excludes packaged/UWP shell
    entries. UWP remains available through Clopen's manual add flow, but the
    searchable library should look like a normal software launcher rather than
    a Windows component inventory.
    """
    if os.name != "nt":
        return []

    command = r'''
[Console]::OutputEncoding=[Text.Encoding]::UTF8
$rows = @(
    $roots = @(
        [Environment]::GetFolderPath('Programs'),
        [Environment]::GetFolderPath('CommonPrograms')
    ) | Where-Object { $_ -and (Test-Path -LiteralPath $_) } | Select-Object -Unique

    $shell = New-Object -ComObject WScript.Shell
    foreach ($root in $roots) {
        Get-ChildItem -LiteralPath $root -Filter *.lnk -File -Recurse -ErrorAction SilentlyContinue | ForEach-Object {
            try {
                $shortcut = $shell.CreateShortcut($_.FullName)
                $target = [Environment]::ExpandEnvironmentVariables([string]$shortcut.TargetPath)
                if ($target -and ([IO.Path]::GetExtension($target) -ieq '.exe')) {
                    [pscustomobject]@{
                        Name = $_.BaseName
                        Path = $target
                        AppID = ''
                        Arguments = [string]$shortcut.Arguments
                        WorkingDirectory = [string]$shortcut.WorkingDirectory
                    }
                }
            } catch {}
        }
    }

)
$rows | ConvertTo-Json -Compress
'''
    try:
        completed = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-WindowStyle", "Hidden", "-Command", command],
            check=True,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        payload = json.loads(completed.stdout or "[]")
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
        return []

    if isinstance(payload, dict):
        payload = [payload]

    results: list[DiscoveredApp] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        name = str(item.get("Name", "")).strip()
        path = os.path.expandvars(str(item.get("Path", "")).strip())
        app_id = str(item.get("AppID", "")).strip()
        if not name or not _looks_like_software(name, path):
            continue
        if path:
            if Path(path).is_file():
                results.append(
                    DiscoveredApp(
                        name=name,
                        path=path,
                        arguments=str(item.get("Arguments", "")).strip(),
                        working_dir=os.path.expandvars(str(item.get("WorkingDirectory", "")).strip()),
                    )
                )
        elif app_id:
            results.append(DiscoveredApp(name=name, app_id=app_id))
    return results


def _dedupe_apps(items: list[DiscoveredApp]) -> list[DiscoveredApp]:
    """Prefer direct EXE launchers and remove duplicate catalog rows."""
    unique: dict[str, DiscoveredApp] = {}
    for item in items:
        if not _looks_like_software(item.name, item.path):
            continue
        path_key = os.path.normcase(item.path) if item.path else ""
        args_key = item.arguments.casefold() if item.arguments else ""
        key = f"exe:{path_key}\0{args_key}" if path_key else f"appid:{item.app_id.casefold()}"
        if key and key not in unique:
            unique[key] = item

    direct_names = {item.name.casefold() for item in unique.values() if item.path}
    filtered = [
        item
        for item in unique.values()
        if item.path or item.name.casefold() not in direct_names
    ]
    return sorted(filtered, key=lambda item: (not bool(item.path), item.name.casefold()))


def search_discovered_apps(apps: list[DiscoveredApp], query: str) -> list[DiscoveredApp]:
    """Filter the catalog while keeping exact/prefix name matches at the top."""
    needle = query.strip().casefold()
    if not needle:
        return sorted(apps, key=lambda app: (not bool(app.path), app.name.casefold()))

    def score(app: DiscoveredApp) -> tuple[int, bool, str]:
        name = app.name.casefold()
        if name == needle:
            rank = 0
        elif name.startswith(needle):
            rank = 1
        elif any(part.startswith(needle) for part in re.split(r"[\s._\-]+", name)):
            rank = 2
        elif needle in name:
            rank = 3
        else:
            rank = 99
        return rank, not bool(app.path), name

    # Search by the user-facing software name only. Hidden executable paths can
    # contain confusing helper names and should not surface unrelated results.
    matched = [app for app in apps if score(app)[0] < 99]
    return sorted(matched, key=score)


_cache_lock = threading.Lock()
_cached_apps: tuple[DiscoveredApp, ...] | None = None


def clear_discovery_cache() -> None:
    global _cached_apps
    with _cache_lock:
        _cached_apps = None


def discover_apps(*, refresh: bool = False) -> list[DiscoveredApp]:
    """Return a cached, searchable local software catalog for Windows."""
    global _cached_apps
    if not refresh:
        with _cache_lock:
            if _cached_apps is not None:
                return list(_cached_apps)

    # Start-menu names are usually the most human-friendly, so put them first.
    # Registry discovery intentionally uses App Paths only; the Uninstall
    # registry inventory is not a software launcher catalog.
    discovered = [app for app in _dedupe_apps([*_shell_apps(), *_registry_apps()]) if app.path]
    with _cache_lock:
        _cached_apps = tuple(discovered)
    return list(discovered)
