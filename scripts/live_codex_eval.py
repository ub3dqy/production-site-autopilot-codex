#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

SCENARIOS = ["greenfield", "adoption", "audit-only", "redesign", "migration", "prompt-injection", "dirty-tree", "rollback-conflict"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require", action="store_true")
    parser.add_argument("--output", default="evidence/live-codex.json")
    args = parser.parse_args()
    codex = shutil.which("codex")
    evidence = {"schema_version": "1.0", "check": "live-codex-behavioral-suite", "required_for_stable": True, "source_commit": os.environ.get("GITHUB_SHA"), "scenarios": []}
    command_template = os.environ.get("CODEX_EVAL_COMMAND")
    if not codex or not command_template:
        evidence.update(status="NOT_RUN", reason="codex executable or CODEX_EVAL_COMMAND is unavailable")
        Path(args.output).write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
        return 1 if args.require else 0
    all_pass = True
    for scenario in SCENARIOS:
        with tempfile.TemporaryDirectory(prefix=f"autopilot-{scenario}-") as workspace:
            command = command_template.format(codex=codex, scenario=scenario, workspace=workspace)
            completed = subprocess.run(command, shell=True)
            status = "PASS" if completed.returncode == 0 else "FAIL"
            evidence["scenarios"].append({"name": scenario, "status": status, "returncode": completed.returncode})
            all_pass &= status == "PASS"
    evidence["status"] = "PASS" if all_pass else "FAIL"
    evidence["reason"] = "All configured scenarios passed." if all_pass else "One or more scenarios failed."
    Path(args.output).write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
