#!/usr/bin/env python3
from __future__ import annotations

import argparse
import compileall
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVIDENCE = ROOT / "build" / "test-evidence.json"
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$", re.I)


def resolve_source_commit(explicit: str | None = None) -> str | None:
    candidates = [explicit, os.environ.get("SOURCE_COMMIT")]
    try:
        completed = subprocess.run(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=15,
        )
        candidates.append(completed.stdout.strip())
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        pass
    for candidate in candidates:
        value = (candidate or "").strip()
        if COMMIT_RE.fullmatch(value):
            return value.lower()
    return None


def run(command: list[str], env: dict[str, str]) -> dict[str, object]:
    started = time.monotonic()
    completed = subprocess.run(command, cwd=ROOT, text=True, env=env)
    return {
        "command": command,
        "returncode": completed.returncode,
        "duration_seconds": round(time.monotonic() - started, 3),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run deterministic repository checks locally.")
    parser.add_argument("--source-commit", help="40-character source commit recorded in evidence.")
    parser.add_argument("--output", default=str(DEFAULT_EVIDENCE), help="Evidence JSON path.")
    args = parser.parse_args()

    source_commit = resolve_source_commit(args.source_commit)
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")
    if source_commit:
        env["SOURCE_COMMIT"] = source_commit

    checks = [
        run([sys.executable, "scripts/verify_repository.py"], env),
        run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"], env),
    ]
    started = time.monotonic()
    compile_ok = compileall.compile_dir(ROOT / "src", quiet=1, force=True)
    checks.append(
        {
            "command": ["compileall", "src"],
            "returncode": 0 if compile_ok else 1,
            "duration_seconds": round(time.monotonic() - started, 3),
        }
    )

    status = "PASS" if all(item["returncode"] == 0 for item in checks) else "FAIL"
    evidence = {
        "schema_version": "1.0",
        "check": "deterministic-repository-suite",
        "status": status,
        "required_for_stable": True,
        "source_commit": source_commit,
        "python": sys.version,
        "platform": sys.platform,
        "checks": checks,
    }
    evidence_path = Path(args.output)
    if not evidence_path.is_absolute():
        evidence_path = ROOT / evidence_path
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(evidence, indent=2))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
