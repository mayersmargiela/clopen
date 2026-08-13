from __future__ import annotations

import json
import os
from pathlib import Path

from .models import AppGroup


class ConfigError(RuntimeError):
    pass


def _default_appdata() -> Path:
    return Path(os.environ.get("APPDATA", Path.home()))


class ConfigStore:
    """Load and save Clopen's own configuration."""

    CURRENT_VERSION = 2

    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path else _default_appdata() / "Clopen" / "config.json"
        self.source = self.path
        self.groups: list[AppGroup] = []

    def load(self) -> list[AppGroup]:
        self.source = self.path
        if not self.path.exists():
            self.groups = []
            return self.groups
        try:
            data = json.loads(self.path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ConfigError(f"无法读取配置：{self.path}\n{exc}") from exc
        if not isinstance(data, dict) or not isinstance(data.get("groups", []), list):
            raise ConfigError(f"配置格式不正确：{self.path}")

        version = int(data.get("version", 1) or 1)
        groups_data = data.get("groups", [])

        # v1 desktop entries defaulted to normal privileges. Clopen v0.2.1
        # changes the product default to administrator launch because many game,
        # streaming and helper apps otherwise fail to open correctly. This
        # one-time migration also updates existing combinations immediately.
        if version < 2:
            for group in groups_data:
                if not isinstance(group, dict):
                    continue
                for entry in group.get("entries", []):
                    if not isinstance(entry, dict):
                        continue
                    is_desktop_app = bool(entry.get("path")) and not any(
                        bool(entry.get(flag)) for flag in ("is_uwp", "is_folder", "is_file")
                    )
                    is_url_only = bool(entry.get("url")) and not bool(entry.get("path"))
                    if is_desktop_app and not is_url_only:
                        entry["run_as_admin"] = True

        self.groups = [AppGroup.from_dict(item) for item in groups_data]
        return self.groups

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {"version": self.CURRENT_VERSION, "groups": [group.to_dict() for group in self.groups]}
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        self.source = self.path
