#!/usr/bin/env python3
from __future__ import annotations

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
        "README.md", "LICENSE.md", "SECURITY.md", "VERSION",
        "src/production_site_autopilot/policy.py",
        "plugin/.codex-plugin/plugin.json",
        "plugin/skills/production-site-autopilot/SKILL.md",
        "schemas/run-result.schema.json",
        "evidence/live-codex.json", "evidence/windows-native.json",
        ".github/workflows/ci.yml", ".github/workflows/release.yml",
    ]
    missing = [path for path in required if not (ROOT / path).is_file()]
    if missing:
        fail("missing required files: " + ", ".join(missing))
    plugin = json.loads((ROOT / "plugin/.codex-plugin/plugin.json").read_text(encoding="utf-8"))
    if plugin.get("version") != version or plugin.get("entry_skill") != "production-site-autopilot":
        fail("plugin manifest is inconsistent")
    init_text = (ROOT / "src/production_site_autopilot/__init__.py").read_text(encoding="utf-8")
    if f'__version__ = "{version}"' not in init_text:
        fail("runtime version does not match VERSION")
    for evidence_path in (ROOT / "evidence").glob("*.json"):
        evidence = json.loads(evidence_path.read_text(encoding="utf-8-sig"))
        if evidence.get("status") not in {"PASS", "FAIL", "NOT_RUN"}:
            fail(f"invalid evidence status: {evidence_path}")
        if evidence.get("status") == "PASS" and not evidence.get("source_commit"):
            fail(f"PASS evidence lacks source_commit: {evidence_path}")
    if (ROOT / "prepare_editions.py").exists() or (ROOT / "packages/source-bundle-v7.1.0").exists():
        fail("opaque source transport remains")
    forbidden = "codex-plugin-" + "cc"
    for path in ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts or path.stat().st_size > 2_000_000:
            continue
        if path.is_symlink():
            fail(f"symlink committed: {path.relative_to(ROOT)}")
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if forbidden in text:
            fail(f"external source dependency remains: {path.relative_to(ROOT)}")
    print("repository integrity: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
