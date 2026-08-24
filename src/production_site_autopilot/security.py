from __future__ import annotations

import fnmatch
import os
import re
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

MAX_TRACKED_BYTES = 5 * 1024 * 1024
EXCLUDED_DIRS = frozenset({
    ".git", ".production-site", ".venv", "venv", "__pycache__", "node_modules",
    "dist", "build", ".next", ".astro", "coverage", ".cache",
})
SECRET_DIR_NAMES = frozenset({".ssh", ".aws", ".gnupg", "secrets", "credentials", "private-keys"})
SECRET_BASENAME_PATTERNS = (
    ".env", ".env.*", "*.pem", "*.key", "*.p12", "*.pfx", "*.jks",
    "id_rsa", "id_ed25519", "credentials", "credentials.json", "service-account*.json",
    "*secret*.json", "*secrets*.yml", "*secrets*.yaml",
)
PROMPT_INJECTION_PATTERNS = (
    re.compile(r"ignore\s+(all\s+)?previous\s+instructions", re.I),
    re.compile(r"(reveal|print|send|upload|exfiltrate).{0,60}(secret|token|password|credential)", re.I | re.S),
    re.compile(r"(disable|bypass|override).{0,40}(policy|approval|safety|guardrail)", re.I | re.S),
    re.compile(r"(curl|wget|invoke-webrequest).{0,160}(token|secret|password|credential|\$env)", re.I | re.S),
    re.compile(r"treat\s+(this|the)\s+(file|document).{0,40}(system|developer)\s+message", re.I | re.S),
)


class UnsafePathError(ValueError):
    pass


@dataclass(frozen=True)
class FileClassification:
    path: str
    protected: bool
    oversized: bool
    prompt_injection: bool
    reason: str | None = None


def _is_link_or_reparse(path: Path) -> bool:
    try:
        info = path.lstat()
    except OSError:
        return False
    if stat.S_ISLNK(info.st_mode):
        return True
    attributes = getattr(info, "st_file_attributes", 0)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return bool(attributes & reparse_flag)


def is_secret_path(path: Path | str) -> bool:
    candidate = Path(path)
    lowered_parts = {part.lower() for part in candidate.parts}
    if lowered_parts & SECRET_DIR_NAMES:
        return True
    name = candidate.name.lower()
    return any(fnmatch.fnmatch(name, pattern.lower()) for pattern in SECRET_BASENAME_PATTERNS)


def contains_prompt_injection(text: str) -> bool:
    return any(pattern.search(text) for pattern in PROMPT_INJECTION_PATTERNS)


def _reject_managed_path_links(root: Path, candidate: Path) -> None:
    try:
        relative = candidate.absolute().relative_to(root)
    except ValueError as exc:
        raise UnsafePathError("path is outside workspace") from exc
    cursor = root
    for part in relative.parts:
        cursor = cursor / part
        if cursor.exists() and _is_link_or_reparse(cursor):
            raise UnsafePathError(f"symlink or reparse point is not allowed: {cursor}")


def safe_path(root: Path | str, candidate: Path | str) -> Path:
    root_path = Path(root).resolve()
    raw = Path(candidate)
    if not raw.is_absolute():
        raw = root_path / raw
    _reject_managed_path_links(root_path, raw)
    resolved = raw.resolve(strict=False)
    try:
        resolved.relative_to(root_path)
    except ValueError as exc:
        raise UnsafePathError(f"path escapes workspace: {candidate}") from exc
    return resolved


def iter_project_files(root: Path | str) -> Iterable[Path]:
    root_path = Path(root).resolve()
    for current, dirnames, filenames in os.walk(root_path, topdown=True, followlinks=False):
        current_path = Path(current)
        retained: list[str] = []
        for dirname in sorted(dirnames):
            candidate = current_path / dirname
            if dirname in EXCLUDED_DIRS or _is_link_or_reparse(candidate):
                continue
            retained.append(dirname)
        dirnames[:] = retained
        for filename in sorted(filenames):
            path = current_path / filename
            try:
                relative = path.relative_to(root_path)
            except ValueError:
                continue
            if any(part in EXCLUDED_DIRS for part in relative.parts):
                continue
            if _is_link_or_reparse(path) or not path.is_file():
                continue
            yield path


def classify_file(root: Path | str, path: Path | str) -> FileClassification:
    root_path = Path(root).resolve()
    file_path = safe_path(root_path, path)
    relative = file_path.relative_to(root_path).as_posix()
    protected = is_secret_path(Path(relative))
    size = file_path.stat().st_size if file_path.exists() else 0
    oversized = size > MAX_TRACKED_BYTES
    injection = False
    if file_path.exists() and not protected and not oversized:
        try:
            injection = contains_prompt_injection(file_path.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            pass
    reason = None
    if protected:
        reason = "secret-like path"
    elif oversized:
        reason = "file exceeds tracked size limit"
    elif injection:
        reason = "project content contains untrusted instruction-like text"
    return FileClassification(relative, protected, oversized, injection, reason)
