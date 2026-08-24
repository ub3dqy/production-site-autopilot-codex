#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXED_ZIP_TIME = (2026, 1, 1, 0, 0, 0)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def selected_files(kind: str) -> list[Path]:
    excluded = {".git", "dist", "build", ".production-site", "__pycache__", ".pytest_cache"}
    roots = ["VERSION", "README.md", "LICENSE.md", "plugin", "installers", "schemas", "src"] if kind == "user" else [
        "VERSION", "README.md", "LICENSE.md", "SECURITY.md", "pyproject.toml", "plugin", "installers",
        "schemas", "src", "scripts", "tests", "fixtures", "docs", "evidence", ".github",
    ]
    paths: list[Path] = []
    for item in roots:
        path = ROOT / item
        if path.is_file():
            paths.append(path)
        elif path.is_dir():
            for child in path.rglob("*"):
                if child.is_file() and not child.is_symlink() and not any(part in excluded for part in child.relative_to(ROOT).parts):
                    paths.append(child)
    return sorted(set(paths), key=lambda value: value.relative_to(ROOT).as_posix())


def write_zip(output: Path, prefix: str, paths: list[Path]) -> dict[str, str]:
    manifest: dict[str, str] = {}
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in paths:
            relative = path.relative_to(ROOT).as_posix()
            data = path.read_bytes()
            info = zipfile.ZipInfo(f"{prefix}/{relative}", FIXED_ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o755 if path.suffix in {".sh", ".py"} else 0o644) << 16
            archive.writestr(info, data)
            manifest[relative] = hashlib.sha256(data).hexdigest()
        info = zipfile.ZipInfo(f"{prefix}/MANIFEST.sha256.json", FIXED_ZIP_TIME)
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o644 << 16
        archive.writestr(info, (json.dumps(manifest, sort_keys=True, indent=2) + "\n").encode())
    return manifest


def stable_gate(version: str) -> None:
    if "-" in version:
        return
    for name in ("live-codex.json", "windows-native.json"):
        evidence = json.loads((ROOT / "evidence" / name).read_text(encoding="utf-8-sig"))
        if evidence.get("required_for_stable") and evidence.get("status") != "PASS":
            raise SystemExit(f"stable release blocked: {name} is {evidence.get('status')}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="dist")
    parser.add_argument("--skip-checks", action="store_true")
    args = parser.parse_args()
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    stable_gate(version)
    if not args.skip_checks:
        subprocess.run([sys.executable, "scripts/run_checks.py"], cwd=ROOT, check=True)
    output = (ROOT / args.output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    names = {
        "user": f"production-site-autopilot-codex-user-v{version}",
        "engineering": f"production-site-autopilot-codex-engineering-v{version}",
    }
    archives: dict[str, str] = {}
    counts: dict[str, int] = {}
    for kind, prefix in names.items():
        archive = output / f"{prefix}.zip"
        manifest = write_zip(archive, prefix, selected_files(kind))
        archives[archive.name] = sha256(archive)
        counts[kind] = len(manifest)
    (output / "SHA256SUMS").write_text("".join(f"{value}  {name}\n" for name, value in sorted(archives.items())), encoding="utf-8")
    test_path = ROOT / "build/test-evidence.json"
    test_evidence = json.loads(test_path.read_text(encoding="utf-8")) if test_path.exists() else {"schema_version": "1.0", "check": "deterministic-repository-suite", "status": "NOT_RUN"}
    (output / "test-evidence.json").write_text(json.dumps(test_evidence, indent=2) + "\n", encoding="utf-8")
    sbom = {
        "bomFormat": "CycloneDX", "specVersion": "1.5", "version": 1,
        "metadata": {"component": {"type": "application", "name": "production-site-autopilot", "version": version}},
        "components": [],
        "properties": [{"name": f"{kind}.file.count", "value": str(count)} for kind, count in counts.items()],
    }
    (output / "sbom.cdx.json").write_text(json.dumps(sbom, indent=2) + "\n", encoding="utf-8")
    provenance = {
        "schema_version": "1.0", "version": version, "source_commit": os.environ.get("GITHUB_SHA"),
        "builder": os.environ.get("GITHUB_WORKFLOW", "local"),
        "built_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "artifacts": archives,
    }
    (output / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"version": version, "artifacts": archives}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
