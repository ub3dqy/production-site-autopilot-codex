#!/usr/bin/env python3
from __future__ import annotations

import ast
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def fail(message: str) -> None:
    raise SystemExit(message)


def main() -> int:
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    if not re.fullmatch(r"\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?", version):
        fail(f"invalid VERSION: {version}")

    required = [
        "README.md",
        "RELEASE_NOTES.md",
        "LICENSE.md",
        "SECURITY.md",
        "VERSION",
        "src/production_site_autopilot/policy.py",
        "plugin/.codex-plugin/plugin.json",
        "plugin/skills/production-site-autopilot/SKILL.md",
        "schemas/run-result.schema.json",
        "evidence/live-codex.json",
        "evidence/windows-native.json",
        "scripts/run_checks.py",
        "scripts/verify_local.py",
        "scripts/build_release.py",
        "docs/local-verification.md",
        "VERIFY_LOCAL_WINDOWS.cmd",
        "VERIFY_LOCAL.sh",
    ]
    missing = [path for path in required if not (ROOT / path).is_file()]
    if missing:
        fail("missing required files: " + ", ".join(missing))

    workflow_dir = ROOT / ".github" / "workflows"
    if workflow_dir.is_dir() and any(path.suffix in {".yml", ".yaml"} for path in workflow_dir.iterdir() if path.is_file()):
        fail("mandatory GitHub Actions workflows remain; local verification must be canonical")

    plugin = json.loads((ROOT / "plugin/.codex-plugin/plugin.json").read_text(encoding="utf-8"))
    if plugin.get("version") != version or plugin.get("entry_skill") != "production-site-autopilot":
        fail("plugin manifest is inconsistent")

    init_text = (ROOT / "src/production_site_autopilot/__init__.py").read_text(encoding="utf-8")
    if f'__version__ = "{version}"' not in init_text:
        fail("runtime version does not match VERSION")
    cli_text = (ROOT / "src/production_site_autopilot/cli.py").read_text(encoding="utf-8")
    if f'version="{version}"' not in cli_text:
        fail("CLI version does not match VERSION")
    if version not in (ROOT / "README.md").read_text(encoding="utf-8"):
        fail("README does not mention VERSION")
    if version not in (ROOT / "RELEASE_NOTES.md").read_text(encoding="utf-8"):
        fail("release notes do not match VERSION")

    for evidence_path in sorted((ROOT / "evidence").glob("*.json")):
        evidence = json.loads(evidence_path.read_text(encoding="utf-8-sig"))
        if evidence.get("status") not in {"PASS", "FAIL", "NOT_RUN"}:
            fail(f"invalid evidence status: {evidence_path}")
        if evidence.get("status") == "PASS" and not re.fullmatch(r"[0-9a-f]{40}", str(evidence.get("source_commit", "")), re.I):
            fail(f"PASS evidence lacks a full source_commit: {evidence_path}")

    if (ROOT / "prepare_editions.py").exists() or (ROOT / "packages/source-bundle-v7.1.0").exists():
        fail("opaque source transport remains")

    for path in [*(ROOT / "src").rglob("*.py"), *(ROOT / "scripts").rglob("*.py"), *(ROOT / "tests").rglob("*.py")]:
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as exc:
            fail(f"invalid Python syntax in {path.relative_to(ROOT)}: {exc}")

    forbidden_external_source = "codex-plugin-" + "cc"
    forbidden_action_env = ("GITHUB_" + "SHA", "GITHUB_" + "WORKFLOW")
    for path in ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts or path.stat().st_size > 2_000_000:
            continue
        if path.is_symlink():
            fail(f"symlink committed: {path.relative_to(ROOT)}")
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if forbidden_external_source in text:
            fail(f"external source dependency remains: {path.relative_to(ROOT)}")
        if path.suffix in {".py", ".ps1", ".sh", ".cmd"} and any(name in text for name in forbidden_action_env):
            fail(f"mandatory GitHub Actions environment dependency remains: {path.relative_to(ROOT)}")

    print("repository integrity: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
