from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIRS = ("src", "tests", "tools")


def main() -> int:
    checked = 0
    for directory in SOURCE_DIRS:
        for path in sorted((ROOT / directory).rglob("*.py")):
            source = path.read_text(encoding="utf-8", errors="strict")
            ast.parse(source, filename=str(path))
            checked += 1
    print(f"PASS - parsed {checked} Python files without writing bytecode")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
