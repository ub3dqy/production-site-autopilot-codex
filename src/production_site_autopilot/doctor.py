from __future__ import annotations

import os
import platform
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

from .detect import detect
from .security import classify_file, iter_project_files


def _writable(path: Path) -> bool:
    try:
        descriptor, probe_name = tempfile.mkstemp(prefix=".production-site-write-probe-", dir=path)
        os.close(descriptor)
        Path(probe_name).unlink(missing_ok=True)
        return True
    except OSError:
        return False


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
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "git_available": shutil.which("git") is not None,
        "workspace": str(root_path),
        "workspace_writable": root_path.exists() and root_path.is_dir() and _writable(root_path),
        "detection": detection.to_dict(),
        "protected_files": protected,
        "oversized_files": oversized,
        "untrusted_instruction_files": injections,
    }
