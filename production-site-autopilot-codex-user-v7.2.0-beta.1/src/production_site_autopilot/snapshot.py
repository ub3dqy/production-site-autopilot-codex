from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any

from .security import classify_file, iter_project_files, safe_path

SCHEMA_VERSION = "1.0"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_text(root: Path, *args: str) -> str | None:
    try:
        completed = subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None
    return completed.stdout


class SnapshotManager:
    def __init__(self, root: Path | str, state_dir: Path | str | None = None) -> None:
        self.root = Path(root).resolve()
        self.state_dir = safe_path(self.root, state_dir or ".production-site")
        self.runs_dir = self.state_dir / "runs"
        self.runs_dir.mkdir(parents=True, exist_ok=True)

    def _run_dir(self, run_id: str) -> Path:
        if not run_id or any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.:" for ch in run_id):
            raise ValueError("invalid run id")
        return safe_path(self.root, self.runs_dir / run_id)

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
                "backup": None,
            }
            if not item["protected"]:
                target = backup_dir / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, target)
                item["backup"] = target.relative_to(run_dir).as_posix()
            entries.append(item)
        manifest = {
            "schema_version": SCHEMA_VERSION,
            "run_id": run_id,
            "workspace": str(self.root),
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "git_head": (_git_text(self.root, "rev-parse", "HEAD") or "").strip() or None,
            "git_status": _git_text(self.root, "status", "--porcelain=v1", "--untracked-files=all"),
            "git_diff": _git_text(self.root, "diff", "--binary", "--no-ext-diff"),
            "baseline": entries,
            "after": None,
            "changed": [],
        }
        (run_dir / "baseline.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
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
                "protected": classification.protected or classification.oversized,
            }
        changed: list[dict[str, Any]] = []
        for relative in sorted(set(baseline) | set(current)):
            before = baseline.get(relative)
            after = current.get(relative)
            if before is None:
                changed.append({"path": relative, "kind": "created", "before_sha256": None, "after_sha256": after["sha256"], "protected": after["protected"]})
            elif after is None:
                changed.append({"path": relative, "kind": "deleted", "before_sha256": before["sha256"], "after_sha256": None, "protected": before["protected"]})
            elif before["sha256"] != after["sha256"]:
                changed.append({"path": relative, "kind": "modified", "before_sha256": before["sha256"], "after_sha256": after["sha256"], "protected": before["protected"] or after["protected"]})
        protected_changes = [item["path"] for item in changed if item["protected"]]
        if protected_changes:
            raise PermissionError("protected/oversized files changed: " + ", ".join(protected_changes))
        manifest["after"] = list(current.values())
        manifest["changed"] = changed
        manifest["finalized_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (run_dir / "changed-files.json").write_text(json.dumps(changed, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return manifest

    def rollback(self, run_id: str, *, force: bool = False) -> dict[str, Any]:
        run_dir = self._run_dir(run_id)
        manifest = json.loads((run_dir / "baseline.json").read_text(encoding="utf-8"))
        if manifest.get("after") is None:
            raise RuntimeError("run has not been finalized")
        baseline = {item["path"]: item for item in manifest["baseline"]}
        conflicts: list[str] = []
        for item in manifest["changed"]:
            target = safe_path(self.root, item["path"])
            current_hash = sha256_file(target) if target.is_file() else None
            if current_hash != item["after_sha256"] and not force:
                conflicts.append(item["path"])
        if conflicts:
            raise RuntimeError("rollback conflict: " + ", ".join(conflicts))
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
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(backup, target)
            os.chmod(target, before["mode"])
            restored.append(relative)
        result = {
            "schema_version": SCHEMA_VERSION,
            "run_id": run_id,
            "rolled_back_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "restored": restored,
            "removed": removed,
            "force": force,
        }
        (run_dir / "rollback.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return result
