from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any

from .security import classify_file, iter_project_files, safe_path

SCHEMA_VERSION = "1.0"
RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_bytes(root: Path, *args: str) -> bytes | None:
    try:
        completed = subprocess.run(
            ["git", "-C", str(root), *args],
            check=True,
            capture_output=True,
            timeout=20,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None
    return completed.stdout


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp-" + uuid.uuid4().hex)
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


def _atomic_write_json(path: Path, value: Any) -> None:
    _atomic_write_text(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


class SnapshotManager:
    def __init__(self, root: Path | str, state_dir: Path | str | None = None) -> None:
        self.root = Path(root).resolve()
        self.state_dir = safe_path(self.root, state_dir or ".production-site")
        self.runs_dir = self.state_dir / "runs"
        self.runs_dir.mkdir(parents=True, exist_ok=True)

    def _validate_run_id(self, run_id: str) -> str:
        if not RUN_ID_RE.fullmatch(run_id):
            raise ValueError("run id must match [A-Za-z0-9][A-Za-z0-9._-]{0,127}")
        return run_id

    def _run_dir(self, run_id: str) -> Path:
        return safe_path(self.root, self.runs_dir / self._validate_run_id(run_id))

    def create(self, run_id: str | None = None) -> dict[str, Any]:
        run_id = run_id or time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()) + "-" + uuid.uuid4().hex[:8]
        run_dir = self._run_dir(run_id)
        if run_dir.exists():
            raise FileExistsError(f"run already exists: {run_id}")
        backup_dir = run_dir / "baseline-files"
        backup_dir.mkdir(parents=True)
        entries: list[dict[str, Any]] = []
        for path in iter_project_files(self.root):
            classification = classify_file(self.root, path)
            relative = path.relative_to(self.root).as_posix()
            item: dict[str, Any] = {
                "path": relative,
                "exists": True,
                "sha256": sha256_file(path),
                "size": path.stat().st_size,
                "mode": stat.S_IMODE(path.stat().st_mode),
                "protected": classification.protected or classification.oversized,
                "protection_reason": classification.reason if classification.protected or classification.oversized else None,
                "backup": None,
            }
            if not item["protected"]:
                target = safe_path(run_dir, backup_dir / relative)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, target)
                if sha256_file(target) != item["sha256"]:
                    raise RuntimeError(f"baseline backup verification failed: {relative}")
                item["backup"] = target.relative_to(run_dir).as_posix()
            entries.append(item)

        status_bytes = _git_bytes(self.root, "status", "--porcelain=v1", "--untracked-files=all")
        diff_bytes = _git_bytes(self.root, "diff", "--binary", "--no-ext-diff")
        head_bytes = _git_bytes(self.root, "rev-parse", "HEAD")
        manifest = {
            "schema_version": SCHEMA_VERSION,
            "run_id": run_id,
            "workspace": str(self.root),
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "git_head": head_bytes.decode("utf-8", errors="replace").strip() if head_bytes else None,
            "git_status": status_bytes.decode("utf-8", errors="replace").splitlines() if status_bytes else [],
            "git_dirty_diff": {
                "stored": False,
                "reason": "raw diff may contain secrets; only digest and byte count are recorded",
                "sha256": sha256_bytes(diff_bytes) if diff_bytes is not None else None,
                "bytes": len(diff_bytes) if diff_bytes is not None else None,
            },
            "baseline": entries,
            "after": None,
            "changed": [],
        }
        _atomic_write_json(run_dir / "baseline.json", manifest)
        _atomic_write_text(
            run_dir / "rollback.md",
            "# Rollback\n\n"
            f"Run ID: `{run_id}`\n\n"
            "Verify first:\n\n"
            f"`python -m production_site_autopilot verify-rollback {run_id} .`\n\n"
            "Apply only when there are no conflicts:\n\n"
            f"`python -m production_site_autopilot rollback {run_id} .`\n",
        )
        return manifest

    def finalize(self, run_id: str) -> dict[str, Any]:
        run_dir = self._run_dir(run_id)
        manifest_path = run_dir / "baseline.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        baseline = {item["path"]: item for item in manifest["baseline"]}
        current: dict[str, dict[str, Any]] = {}
        for path in iter_project_files(self.root):
            relative = path.relative_to(self.root).as_posix()
            classification = classify_file(self.root, path)
            current[relative] = {
                "path": relative,
                "exists": True,
                "sha256": sha256_file(path),
                "size": path.stat().st_size,
                "mode": stat.S_IMODE(path.stat().st_mode),
                "protected": classification.protected or classification.oversized,
            }
        changed: list[dict[str, Any]] = []
        for relative in sorted(set(baseline) | set(current)):
            before = baseline.get(relative)
            after = current.get(relative)
            if before is None:
                changed.append({"path": relative, "kind": "created", "before_sha256": None, "after_sha256": after["sha256"], "after_mode": after["mode"], "protected": after["protected"]})
            elif after is None:
                changed.append({"path": relative, "kind": "deleted", "before_sha256": before["sha256"], "after_sha256": None, "after_mode": None, "protected": before["protected"]})
            elif before["sha256"] != after["sha256"] or before["mode"] != after["mode"]:
                changed.append({"path": relative, "kind": "modified", "before_sha256": before["sha256"], "after_sha256": after["sha256"], "after_mode": after["mode"], "protected": before["protected"] or after["protected"]})
        protected_changes = [item["path"] for item in changed if item["protected"]]
        if protected_changes:
            _atomic_write_json(run_dir / "protected-changes.json", {"paths": protected_changes, "status": "BLOCKED"})
            raise PermissionError("protected or oversized files changed: " + ", ".join(protected_changes))
        manifest["after"] = list(current.values())
        manifest["changed"] = changed
        manifest["finalized_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        _atomic_write_json(manifest_path, manifest)
        _atomic_write_json(run_dir / "changed-files.json", changed)
        return manifest

    def verify_rollback(self, run_id: str) -> dict[str, Any]:
        run_dir = self._run_dir(run_id)
        manifest = json.loads((run_dir / "baseline.json").read_text(encoding="utf-8"))
        if manifest.get("after") is None:
            raise RuntimeError("run has not been finalized")
        baseline = {item["path"]: item for item in manifest["baseline"]}
        conflicts: list[str] = []
        damaged_backups: list[str] = []
        for item in manifest["changed"]:
            target = safe_path(self.root, item["path"])
            current_hash = sha256_file(target) if target.is_file() else None
            current_mode = stat.S_IMODE(target.stat().st_mode) if target.is_file() else None
            if current_hash != item["after_sha256"] or current_mode != item["after_mode"]:
                conflicts.append(item["path"])
            before = baseline.get(item["path"])
            if before and not before["protected"]:
                backup = safe_path(run_dir, before["backup"])
                if not backup.is_file() or sha256_file(backup) != before["sha256"]:
                    damaged_backups.append(item["path"])
        return {
            "schema_version": SCHEMA_VERSION,
            "run_id": run_id,
            "ready": not conflicts and not damaged_backups,
            "conflicts": conflicts,
            "damaged_backups": damaged_backups,
        }

    def rollback(self, run_id: str, *, force: bool = False) -> dict[str, Any]:
        verification = self.verify_rollback(run_id)
        if verification["damaged_backups"]:
            raise RuntimeError("rollback backup integrity failure: " + ", ".join(verification["damaged_backups"]))
        if verification["conflicts"] and not force:
            raise RuntimeError("rollback conflict: " + ", ".join(verification["conflicts"]))

        run_dir = self._run_dir(run_id)
        manifest = json.loads((run_dir / "baseline.json").read_text(encoding="utf-8"))
        baseline = {item["path"]: item for item in manifest["baseline"]}
        restored: list[str] = []
        removed: list[str] = []
        for item in manifest["changed"]:
            relative = item["path"]
            target = safe_path(self.root, relative)
            before = baseline.get(relative)
            if before is None:
                if target.exists():
                    if not target.is_file():
                        raise RuntimeError(f"refusing to remove non-file: {relative}")
                    target.unlink()
                    removed.append(relative)
                continue
            if before["protected"]:
                raise PermissionError(f"protected file cannot be restored from evidence: {relative}")
            backup = safe_path(run_dir, before["backup"])
            if sha256_file(backup) != before["sha256"]:
                raise RuntimeError(f"rollback backup integrity failure: {relative}")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(backup, target)
            os.chmod(target, before["mode"])
            if sha256_file(target) != before["sha256"]:
                raise RuntimeError(f"rollback restore verification failed: {relative}")
            restored.append(relative)
        result = {
            "schema_version": SCHEMA_VERSION,
            "run_id": run_id,
            "rolled_back_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "restored": restored,
            "removed": removed,
            "force": force,
            "verified": True,
        }
        _atomic_write_json(run_dir / "rollback.json", result)
        return result
