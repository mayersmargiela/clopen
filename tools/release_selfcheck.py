from __future__ import annotations

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {".py", ".toml", ".ps1", ".cmd", ".txt", ".md", ".qml", ".yml", ".yaml"}
FORBIDDEN_DIRS = {".venv", "build", "dist", "__pycache__", "artifacts"}
OLD_UNDERSCORE = "mayers" + "_batch"
OLD_HYPHEN = "mayers" + "-batch"
GLOBAL_KILL_COMMANDS = ("task" + "kill", "wmic" + " process", "kill" + "all")
KNOWN_SOURCE_NAME = "batch" + "go"
PRIVATE_PATH_MARKERS = ("c:\\users\\", "d:\\agents for mayers\\", "appdata\\local\\temp")
SECRET_PATTERNS = (
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
)
REQUIRED_PUBLIC_FILES = (
    "README.md",
    "LICENSE",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "CODE_OF_CONDUCT.md",
    "THIRD_PARTY_NOTICES.md",
    "PRIVACY.md",
)


def source_text() -> str:
    chunks: list[str] = []
    for path in ROOT.rglob("*"):
        if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES:
            chunks.append(path.read_text(encoding="utf-8", errors="strict"))
    return "\n".join(chunks)


def main() -> int:
    text = source_text()
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    config = (ROOT / "src" / "clopen" / "config.py").read_text(encoding="utf-8")
    launcher = (ROOT / "src" / "clopen" / "launcher.py").read_text(encoding="utf-8")
    process_control = (ROOT / "src" / "clopen" / "process_control.py").read_text(encoding="utf-8")
    package_init = (ROOT / "src" / "clopen" / "__init__.py").read_text(encoding="utf-8")
    qml_app = (ROOT / "src" / "clopen" / "qml_app.py").read_text(encoding="utf-8")
    main_qml = (ROOT / "src" / "clopen" / "qml" / "Main.qml").read_text(encoding="utf-8")
    glass_button = (ROOT / "src" / "clopen" / "qml" / "GlassButton.qml").read_text(encoding="utf-8")
    entry = (ROOT / "src" / "clopen_entry.py").read_text(encoding="utf-8")
    module_entry = (ROOT / "src" / "clopen" / "__main__.py").read_text(encoding="utf-8")

    generated_dirs = [
        path.relative_to(ROOT).as_posix()
        for path in ROOT.rglob("*")
        if path.is_dir() and (path.name in FORBIDDEN_DIRS or path.name.endswith(".egg-info"))
    ]
    user_configs = [
        path.relative_to(ROOT).as_posix()
        for path in ROOT.rglob("config.json")
        if path.is_file()
    ]

    checks = [
        ("Liquid Glass version is 0.6.0 everywhere", 'version = "0.6.0"' in pyproject and '__version__ = "0.6.0"' in package_init),
        ("console command uses the Liquid Glass shell", 'clopen = "clopen.qml_app:main"' in pyproject),
        ("package data includes resources and QML", 'clopen = ["resources/*", "qml/*.qml"]' in pyproject),
        ("clopen package directory exists", (ROOT / "src" / "clopen" / "__init__.py").is_file()),
        ("old package directory is absent", not (ROOT / "src" / OLD_UNDERSCORE).exists()),
        ("old identifiers are absent", OLD_UNDERSCORE not in text.lower() and OLD_HYPHEN not in text.lower()),
        ("known-source name is absent from public text", KNOWN_SOURCE_NAME not in text.lower()),
        ("required public documents exist", all((ROOT / name).is_file() for name in REQUIRED_PUBLIC_FILES)),
        ("personal machine paths are absent", not any(marker in text.lower() for marker in PRIVATE_PATH_MARKERS)),
        ("common secret formats are absent", not any(pattern.search(text) for pattern in SECRET_PATTERNS)),
        ("config uses APPDATA/Clopen/config.json", '_default_appdata() / "Clopen" / "config.json"' in config),
        ("entry imports the Liquid Glass shell", "from clopen.qml_app import main" in entry),
        ("python -m clopen uses the Liquid Glass shell", "from .qml_app import main" in module_entry),
        ("Liquid Glass QML files exist", all((ROOT / "src" / "clopen" / "qml" / name).is_file() for name in ("Main.qml", "GlassPane.qml", "GlassButton.qml", "QuickLauncher.qml", "TrayPopup.qml"))),
        ("main layout remains 920x600 / sidebar 232", "width: 920" in main_qml and "height: 600" in main_qml and "Layout.preferredWidth: 232" in main_qml),
        ("glass action buttons remain present", main_qml.count("GlassButton {") >= 8 and "GlassPane" in glass_button),
        ("Ctrl+Shift+E uses physical-key polling", "GetAsyncKeyState" in qml_app and "_hotkey_watch_loop" in qml_app),
        ("hotkey callback returns to the Qt GUI thread", "hotkeyTriggered" in qml_app and "QueuedConnection" in qml_app),
        ("quick launcher is persistent QWidget popup", "class QuickLauncherPopup" in qml_app and "Qt.WindowType.Popup" in qml_app),
        ("managed launches register a process handle", "session.add_handle" in launcher),
        ("external launch paths stay unmanaged", 'EntryResult(entry.name, "unmanaged"' in launcher),
        ("session close uses Job Object ownership", "TerminateJobObject" in process_control),
        ("no process-name global kill command", not any(command in text.lower() for command in GLOBAL_KILL_COMMANDS)),
        ("PID close is guarded by the live process handle", "_process_is_alive(handle)" in process_control),
        ("no generated directories in public source", not generated_dirs),
        ("no user config in public source", not user_configs),
    ]

    failed = []
    for name, ok in checks:
        print(f"{'PASS' if ok else 'FAIL'} - {name}")
        if not ok:
            failed.append(name)
    if generated_dirs:
        print("Generated directories: " + ", ".join(generated_dirs))
    if user_configs:
        print("User configs: " + ", ".join(user_configs))
    if failed:
        raise SystemExit("Release self-check failed: " + ", ".join(failed))
    print(f"PASS - {len(checks)} release checks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
