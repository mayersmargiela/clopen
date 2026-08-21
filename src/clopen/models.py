from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AppEntry:
    name: str = ""
    path: str = ""
    arguments: str = ""
    working_dir: str = ""
    url: str = ""
    is_uwp: bool = False
    is_folder: bool = False
    is_file: bool = False
    run_as_admin: bool = False

    @classmethod
    def from_dict(cls, data: dict) -> "AppEntry":
        return cls(
            name=str(data.get("name", "")),
            path=str(data.get("path", "")),
            arguments=str(data.get("arguments", "")),
            working_dir=str(data.get("working_dir", "")),
            url=str(data.get("url", "")),
            is_uwp=bool(data.get("is_uwp", False)),
            is_folder=bool(data.get("is_folder", False)),
            is_file=bool(data.get("is_file", False)),
            run_as_admin=bool(data.get("run_as_admin", False)),
        )

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "path": self.path,
            "arguments": self.arguments,
            "working_dir": self.working_dir,
            "url": self.url,
            "is_uwp": self.is_uwp,
            "is_folder": self.is_folder,
            "is_file": self.is_file,
            "run_as_admin": self.run_as_admin,
        }

    @property
    def is_external(self) -> bool:
        """Whether launching this entry cannot be safely owned by this process session."""
        return self.is_uwp or self.is_folder or self.is_file or (not self.path and bool(self.url))


@dataclass
class AppGroup:
    name: str = ""
    entries: list[AppEntry] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "AppGroup":
        return cls(
            name=str(data.get("name", "")),
            entries=[AppEntry.from_dict(item) for item in data.get("entries", [])],
        )

    def to_dict(self) -> dict:
        return {"name": self.name, "entries": [entry.to_dict() for entry in self.entries]}


@dataclass
class EntryResult:
    name: str
    status: str
    detail: str = ""


@dataclass
class LaunchReport:
    group_name: str
    results: list[EntryResult] = field(default_factory=list)

    @property
    def started(self) -> int:
        return sum(result.status == "started" for result in self.results)

    @property
    def unmanaged(self) -> int:
        return sum(result.status == "unmanaged" for result in self.results)

    @property
    def failed(self) -> int:
        return sum(result.status == "failed" for result in self.results)


@dataclass
class CloseReport:
    group_name: str
    closed: int
    detail: str = ""
