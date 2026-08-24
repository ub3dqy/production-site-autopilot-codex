#!/usr/bin/env python3
from __future__ import annotations

import compileall
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "build" / "test-evidence.json"


def run(command: list[str]) -> dict:
    started = time.time()
    completed = subprocess.run(command, cwd=ROOT, text=True)
    return {"command": command, "returncode": completed.returncode, "duration_seconds": round(time.time() - started, 3)}


def main() -> int:
    os.environ["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + os.environ.get("PYTHONPATH", "")
    checks = [
        run([sys.executable, "scripts/verify_repository.py"]),
        run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"]),
    ]
    compile_ok = compileall.compile_dir(ROOT / "src", quiet=1, force=True)
    checks.append({"command": ["compileall", "src"], "returncode": 0 if compile_ok else 1, "duration_seconds": 0})
    status = "PASS" if all(item["returncode"] == 0 for item in checks) else "FAIL"
    evidence = {
        "schema_version": "1.0",
        "check": "deterministic-repository-suite",
        "status": status,
        "required_for_stable": true if False else True,
        "source_commit": os.environ.get("GITHUB_SHA"),
        "python": sys.version,
        "platform": sys.platform,
        "checks": checks,
    }
    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(evidence, indent=2))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
