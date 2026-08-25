#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$", re.I)
DEFAULT_SOURCE_DATE_EPOCH = "1767225600"
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


def resolve_source_commit(explicit: str | None) -> str:
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
    raise SystemExit("Local verification requires --source-commit, SOURCE_COMMIT, or a Git checkout with a full HEAD SHA.")


def run(command: list[str], env: dict[str, str]) -> dict[str, Any]:
    print("+", " ".join(command), flush=True)
    started = time.monotonic()
    completed = subprocess.run(command, cwd=ROOT, env=env, text=True)
    return {
        "command": command,
        "returncode": completed.returncode,
        "duration_seconds": round(time.monotonic() - started, 3),
    }


def verify_checksums(directory: Path) -> dict[str, str]:
    checksum_file = directory / "SHA256SUMS"
    if not checksum_file.is_file():
        raise RuntimeError(f"missing {checksum_file}")
    verified: dict[str, str] = {}
    for line in checksum_file.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        parts = line.split("  ", 1)
        if len(parts) != 2 or not re.fullmatch(r"[0-9a-f]{64}", parts[0]):
            raise RuntimeError(f"invalid SHA256SUMS line: {line!r}")
        expected, name = parts
        target = directory / name
        if not target.is_file():
            raise RuntimeError(f"checksum target is missing: {name}")
        actual = sha256(target)
        if actual != expected:
            raise RuntimeError(f"checksum mismatch for {name}: {actual}")
        verified[name] = actual
    if not verified:
        raise RuntimeError("SHA256SUMS contains no artifacts")
    return verified


def verify_zip(archive_path: Path) -> int:
    with zipfile.ZipFile(archive_path) as archive:
        names = archive.namelist()
        if not names:
            raise RuntimeError(f"empty archive: {archive_path.name}")
        for name in names:
            path = PurePosixPath(name)
            if path.is_absolute() or ".." in path.parts:
                raise RuntimeError(f"unsafe archive path in {archive_path.name}: {name}")
        manifest_names = [name for name in names if name.endswith("/MANIFEST.sha256.json")]
        if len(manifest_names) != 1:
            raise RuntimeError(f"expected one archive manifest in {archive_path.name}")
        manifest_name = manifest_names[0]
        prefix = manifest_name[: -len("MANIFEST.sha256.json")]
        manifest = json.loads(archive.read(manifest_name).decode("utf-8"))
        if not isinstance(manifest, dict):
            raise RuntimeError(f"invalid manifest object in {archive_path.name}")
        for relative, expected in manifest.items():
            member = prefix + relative
            if member not in names:
                raise RuntimeError(f"manifest member missing in {archive_path.name}: {relative}")
            actual = hashlib.sha256(archive.read(member)).hexdigest()
            if actual != expected:
                raise RuntimeError(f"manifest hash mismatch in {archive_path.name}: {relative}")
        content_members = [name for name in names if name != manifest_name and not name.endswith("/")]
        if len(content_members) != len(manifest):
            raise RuntimeError(f"unmanifested archive member in {archive_path.name}")
        return len(manifest)


def load_external_evidence(name: str, source_commit: str) -> dict[str, Any]:
    path = ROOT / "evidence" / name
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    recorded = data.get("source_commit")
    stale = data.get("status") == "PASS" and recorded != source_commit
    raw_scenarios = data.get("scenarios", [])
    scenario_names = {
        item.get("name") if isinstance(item, dict) else item
        for item in raw_scenarios
        if (isinstance(item, str) and item) or (isinstance(item, dict) and item.get("name"))
    }
    missing_scenarios = sorted(REQUIRED_EXTERNAL_SCENARIOS.get(name, set()) - scenario_names)
    incomplete = data.get("status") == "PASS" and bool(missing_scenarios)
    effective_status = "FAIL" if stale or incomplete else data.get("status")
    return {
        "file": name,
        "status": data.get("status"),
        "source_commit": recorded,
        "required_for_stable": bool(data.get("required_for_stable")),
        "reason": data.get("reason"),
        "stale": stale,
        "missing_scenarios": missing_scenarios,
        "effective_status": effective_status,
    }


def write_evidence(output: Path, evidence: dict[str, Any]) -> None:
    build_path = ROOT / "build" / "local-verification.json"
    build_path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(evidence, ensure_ascii=False, indent=2) + "\n"
    build_path.write_text(content, encoding="utf-8")
    output.mkdir(parents=True, exist_ok=True)
    (output / "local-verification.json").write_text(content, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Canonical local verification and beta release builder.")
    parser.add_argument("--source-commit", help="Full 40-character source commit.")
    parser.add_argument("--output-dir", default="dist", help="Final release artifact directory.")
    parser.add_argument("--skip-windows", action="store_true", help="Do not run native Windows lifecycle even on Windows.")
    parser.add_argument("--skip-live", action="store_true", help="Do not run configured live Codex evaluation.")
    parser.add_argument("--require-windows", action="store_true", help="Fail unless current native Windows evidence is PASS.")
    parser.add_argument("--require-live", action="store_true", help="Fail unless current live Codex evidence is PASS.")
    args = parser.parse_args()

    source_commit = resolve_source_commit(args.source_commit)
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
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
    if output.exists():
        shutil.rmtree(output)

    env = os.environ.copy()
    env["SOURCE_COMMIT"] = source_commit
    env["SOURCE_DATE_EPOCH"] = env.get("SOURCE_DATE_EPOCH", DEFAULT_SOURCE_DATE_EPOCH)
    env["AUTOPILOT_BUILDER"] = "local-verification"
    env["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")

    commands: list[dict[str, Any]] = []
    commands.append(run([sys.executable, "scripts/run_checks.py", "--source-commit", source_commit], env))
    deterministic_pass = commands[-1]["returncode"] == 0

    if deterministic_pass and os.name == "nt" and not args.skip_windows:
        powershell = shutil.which("pwsh") or shutil.which("powershell")
        if powershell:
            commands.append(
                run(
                    [powershell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "scripts/windows_smoke.ps1", "-SourceCommit", source_commit],
                    env,
                )
            )
            deterministic_pass &= commands[-1]["returncode"] == 0

    if deterministic_pass and not args.skip_live and shutil.which("codex") and env.get("CODEX_EVAL_COMMAND"):
        commands.append(run([sys.executable, "scripts/live_codex_eval.py", "--source-commit", source_commit], env))
        deterministic_pass &= commands[-1]["returncode"] == 0

    reproducible = False
    archive_hashes: dict[str, str] = {}
    archive_file_counts: dict[str, int] = {}
    packaging_error: str | None = None
    if deterministic_pass:
        try:
            with tempfile.TemporaryDirectory(prefix="autopilot-release-a-") as first_raw, tempfile.TemporaryDirectory(prefix="autopilot-release-b-") as second_raw:
                first = Path(first_raw)
                second = Path(second_raw)
                for target in (first, second):
                    result = run(
                        [
                            sys.executable,
                            "scripts/build_release.py",
                            "--output-dir",
                            str(target),
                            "--skip-checks",
                            "--source-commit",
                            source_commit,
                        ],
                        env,
                    )
                    commands.append(result)
                    if result["returncode"] != 0:
                        raise RuntimeError("release builder failed")
                first_checksums = verify_checksums(first)
                second_checksums = verify_checksums(second)
                if first_checksums != second_checksums:
                    raise RuntimeError("release ZIP hashes are not reproducible")
                for name, digest in sorted(first_checksums.items()):
                    archive_file_counts[name] = verify_zip(first / name)
                    verify_zip(second / name)
                    archive_hashes[name] = digest
                reproducible = True
                shutil.copytree(first, output)
        except (OSError, RuntimeError, ValueError, zipfile.BadZipFile, json.JSONDecodeError) as exc:
            packaging_error = str(exc)

    external = {
        "windows_native": load_external_evidence("windows-native.json", source_commit),
        "live_codex": load_external_evidence("live-codex.json", source_commit),
    }
    beta_eligible = deterministic_pass and reproducible
    stable_eligible = beta_eligible and all(item["effective_status"] == "PASS" for item in external.values())
    requirements_pass = (
        (not args.require_windows or external["windows_native"]["effective_status"] == "PASS")
        and (not args.require_live or external["live_codex"]["effective_status"] == "PASS")
    )
    overall_pass = beta_eligible and requirements_pass

    evidence = {
        "schema_version": "1.0",
        "check": "canonical-local-verification",
        "status": "PASS" if overall_pass else "FAIL",
        "version": version,
        "source_commit": source_commit,
        "verified_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "host": {"platform": platform.platform(), "python": sys.version, "os_name": os.name},
        "github_actions": {"available": False, "required": False},
        "deterministic_suite": "PASS" if deterministic_pass else "FAIL",
        "reproducible_release": "PASS" if reproducible else "FAIL",
        "packaging_error": packaging_error,
        "archives": archive_hashes,
        "archive_file_counts": archive_file_counts,
        "external_evidence": external,
        "beta_release_eligible": beta_eligible,
        "stable_release_eligible": stable_eligible,
        "commands": commands,
    }
    write_evidence(output, evidence)
    print(json.dumps(evidence, ensure_ascii=False, indent=2))
    return 0 if overall_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
