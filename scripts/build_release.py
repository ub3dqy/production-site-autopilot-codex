#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXED_ZIP_TIME = (2026, 1, 1, 0, 0, 0)
DEFAULT_SOURCE_DATE_EPOCH = 1767225600  # 2026-01-01T00:00:00Z
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$", re.I)
REQUIRED_EXTERNAL_SCENARIOS = {
    "windows-native.json": {"cmd-launcher", "powershell-installer", "path-with-spaces", "unicode-path", "non-system-drive", "upgrade", "doctor", "uninstall"},
    "live-codex.json": {"greenfield", "adoption", "audit-only", "redesign", "migration", "prompt-injection", "dirty-tree", "rollback-conflict"},
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


def build_timestamp() -> tuple[int, str]:
    raw = os.environ.get("SOURCE_DATE_EPOCH", str(DEFAULT_SOURCE_DATE_EPOCH))
    try:
        epoch = int(raw)
    except ValueError as exc:
        raise SystemExit(f"invalid SOURCE_DATE_EPOCH: {raw}") from exc
    if epoch < 0:
        raise SystemExit("SOURCE_DATE_EPOCH must be non-negative")
    return epoch, time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(epoch))


def selected_files(kind: str) -> list[Path]:
    excluded = {".git", "dist", "build", ".production-site", "__pycache__", ".pytest_cache"}
    common = [
        "VERSION", "README.md", "RELEASE_NOTES.md", "LICENSE.md",
        "plugin", "installers", "schemas", "src",
    ]
    roots = common if kind == "user" else [
        *common, "SECURITY.md", "pyproject.toml", "scripts", "tests", "fixtures", "docs", "evidence",
        "VERIFY_LOCAL_WINDOWS.cmd", "VERIFY_LOCAL.sh",
    ]
    paths: list[Path] = []
    for item in roots:
        path = ROOT / item
        if path.is_file():
            paths.append(path)
        elif path.is_dir():
            for child in path.rglob("*"):
                relative_parts = child.relative_to(ROOT).parts
                if child.is_file() and not child.is_symlink() and not any(part in excluded for part in relative_parts):
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


def stable_gate(version: str, source_commit: str | None = None) -> None:
    if "-" in version:
        return
    if not source_commit or not COMMIT_RE.fullmatch(source_commit):
        raise SystemExit("stable release blocked: full source commit is required")
    for name in ("live-codex.json", "windows-native.json"):
        evidence = json.loads((ROOT / "evidence" / name).read_text(encoding="utf-8-sig"))
        if not evidence.get("required_for_stable"):
            continue
        if evidence.get("status") != "PASS":
            raise SystemExit(f"stable release blocked: {name} is {evidence.get('status')}")
        if evidence.get("source_commit") != source_commit:
            raise SystemExit(f"stable release blocked: {name} is stale")
        raw_scenarios = evidence.get("scenarios", [])
        scenario_names = {
            item.get("name") if isinstance(item, dict) else item
            for item in raw_scenarios
            if (isinstance(item, str) and item) or (isinstance(item, dict) and item.get("name"))
        }
        missing = sorted(REQUIRED_EXTERNAL_SCENARIOS[name] - scenario_names)
        if missing:
            raise SystemExit(f"stable release blocked: {name} lacks scenarios: {', '.join(missing)}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build deterministic local release artifacts.")
    parser.add_argument("--output-dir", default="dist")
    parser.add_argument("--skip-checks", action="store_true")
    parser.add_argument("--source-commit", help="40-character source commit recorded in provenance.")
    args = parser.parse_args()

    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    source_commit = resolve_source_commit(args.source_commit)

    output = Path(args.output_dir)
    if not output.is_absolute():
        output = (ROOT / output).resolve()
    else:
        output = output.resolve()
    try:
        relative_output = output.relative_to(ROOT)
    except ValueError:
        relative_output = None
    if relative_output is not None and (not relative_output.parts or relative_output.parts[0] not in {"dist", "build"}):
        raise SystemExit(f"unsafe output directory inside repository: {output}")
    output.mkdir(parents=True, exist_ok=True)

    stable_gate(version, source_commit)
    if not args.skip_checks:
        command = [sys.executable, "scripts/run_checks.py"]
        if source_commit:
            command.extend(["--source-commit", source_commit])
        subprocess.run(command, cwd=ROOT, check=True)

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

    (output / "SHA256SUMS").write_text(
        "".join(f"{value}  {name}\n" for name, value in sorted(archives.items())),
        encoding="utf-8",
    )
    test_path = ROOT / "build/test-evidence.json"
    test_evidence = (
        json.loads(test_path.read_text(encoding="utf-8"))
        if test_path.exists()
        else {"schema_version": "1.0", "check": "deterministic-repository-suite", "status": "NOT_RUN"}
    )
    (output / "test-evidence.json").write_text(json.dumps(test_evidence, indent=2) + "\n", encoding="utf-8")

    sbom = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "version": 1,
        "metadata": {"component": {"type": "application", "name": "production-site-autopilot", "version": version}},
        "components": [],
        "properties": [{"name": f"{kind}.file.count", "value": str(count)} for kind, count in counts.items()],
    }
    (output / "sbom.cdx.json").write_text(json.dumps(sbom, indent=2) + "\n", encoding="utf-8")

    epoch, built_at = build_timestamp()
    provenance = {
        "schema_version": "1.0",
        "version": version,
        "source_commit": source_commit,
        "builder": os.environ.get("AUTOPILOT_BUILDER", "local"),
        "source_date_epoch": epoch,
        "built_at": built_at,
        "artifacts": archives,
    }
    (output / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"version": version, "source_commit": source_commit, "artifacts": archives}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
