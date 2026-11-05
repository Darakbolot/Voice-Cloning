"""Run offline syntax and integration checks; fail if any test is skipped."""

import ast
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]


def main():
    names = set(p for p in subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=ROOT
    ).decode().split("\0") if p)
    counts = {".py": 0, ".json": 0}
    for name in sorted(names):
        path = ROOT / name
        if not path.is_file():
            continue
        if path.suffix == ".py":
            ast.parse(path.read_text(encoding="utf-8-sig"), filename=name)
            counts[".py"] += 1
        elif path.suffix == ".json":
            json.loads(path.read_text(encoding="utf-8-sig"))
            counts[".json"] += 1
    print("Syntax checks PASS:", counts)
    # Reuse available web packages for routing tests; model inference is mocked.
    for name in ("speech-demo", "suwawa"):
        packages = ROOT / ".local" / "environments" / name / "Lib" / "site-packages"
        if packages.is_dir():
            sys.path.append(str(packages))
    result = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.discover(str(ROOT / "tests"))
    )
    if result.skipped:
        print("Install the web test dependencies before publishing: flask fastapi httpx python-multipart uvicorn")
    return int(not result.wasSuccessful() or bool(result.skipped))


if __name__ == "__main__":
    raise SystemExit(main())
