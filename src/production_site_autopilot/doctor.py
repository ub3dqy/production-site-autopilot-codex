from __future__ import annotations

import os
import platform
import shutil
import sys
from pathlib import Path
from typing import Any

from .detect import detect
from .security import classify_file, iter_project_files


def run_doctor(root: Path | str) -> dict[str, Any]:
    root_path = Path(root).resolve()
    protected: list[str] = []
    oversized: list[str] = []
    injections: list[str] = []
    for path in iter_project_files(root_path):
        item = classify_file(root_path, path)
        if item.protected:
            protected.append(item.path)
        if item.oversized:
            oversized.append(item.path)
        if item.prompt_injection:
            injections.append(item.path)
    detection = detect(root_path)
    return {
        "schema_version": "1.0",
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "git_available": shutil.which("git") is not None,
        "workspace": str(root_path),
        "workspace_exists": root_path.exists() and root_path.is_dir(),
        "workspace_writable_by_process": os.access(root_path, os.W_OK),
        "doctor_mutated_workspace": False,
        "detection": detection.to_dict(),
        "protected_files": protected,
        "oversized_files": oversized,
        "untrusted_instruction_files": injections,
    }
