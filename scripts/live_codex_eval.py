#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = ["greenfield", "adoption", "audit-only", "redesign", "migration", "prompt-injection", "dirty-tree", "rollback-conflict"]
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require", action="store_true")
    parser.add_argument("--output", default="evidence/live-codex.json")
    parser.add_argument("--source-commit")
    args = parser.parse_args()

    source_commit = resolve_source_commit(args.source_commit)
    codex = shutil.which("codex")
    evidence = {
        "schema_version": "1.0",
        "check": "live-codex-behavioral-suite",
        "required_for_stable": True,
        "source_commit": source_commit,
        "scenarios": [],
    }
    command_template = os.environ.get("CODEX_EVAL_COMMAND")
    output = Path(args.output)
    if not output.is_absolute():
        output = ROOT / output
    output.parent.mkdir(parents=True, exist_ok=True)

    if not codex or not command_template:
        evidence.update(status="NOT_RUN", reason="codex executable or CODEX_EVAL_COMMAND is unavailable")
        output.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
        return 1 if args.require else 0
    if not source_commit:
        evidence.update(status="FAIL", reason="A full source commit is required for live PASS evidence.")
        output.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
        return 1

    all_pass = True
    for scenario in SCENARIOS:
        with tempfile.TemporaryDirectory(prefix=f"autopilot-{scenario}-") as workspace:
            command = command_template.format(codex=codex, scenario=scenario, workspace=workspace)
            completed = subprocess.run(command, shell=True, cwd=ROOT)
            status = "PASS" if completed.returncode == 0 else "FAIL"
            evidence["scenarios"].append({"name": scenario, "status": status, "returncode": completed.returncode})
            all_pass &= status == "PASS"
    evidence["status"] = "PASS" if all_pass else "FAIL"
    evidence["reason"] = "All configured scenarios passed." if all_pass else "One or more scenarios failed."
    output.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
