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
    "dist", "build", ".next", ".astro", "coverage",
})
SECRET_PATTERNS = (
    ".env", ".env.*", "*.pem", "*.key", "*.p12", "*.pfx", "id_rsa", "id_ed25519",
    "credentials", "credentials.*", "credentials.json", "service-account*.json", "*secret*.json",
    ".npmrc", ".pypirc", ".netrc", "auth.json",
)
PROMPT_INJECTION_PATTERNS = (
    re.compile(r"ignore\s+(all\s+)?previous\s+instructions", re.I),
    re.compile(r"(reveal|print|send|upload).{0,40}(secret|token|password|credential)", re.I | re.S),
    re.compile(r"(disable|bypass).{0,30}(policy|approval|safety|guardrail)", re.I | re.S),
    re.compile(r"(curl|wget|invoke-webrequest).{0,120}(token|secret|password|\$env)", re.I | re.S),
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


def is_secret_path(path: Path | str) -> bool:
    name = Path(path).name
    return any(fnmatch.fnmatch(name.lower(), pattern.lower()) for pattern in SECRET_PATTERNS)


def contains_prompt_injection(text: str) -> bool:
    return any(pattern.search(text) for pattern in PROMPT_INJECTION_PATTERNS)


def is_link_or_reparse(path: Path) -> bool:
    """Return True for POSIX symlinks and Windows junction/reparse points."""
    try:
        if path.is_symlink():
            return True
    except OSError:
        return True

    is_junction = getattr(path, "is_junction", None)
    if callable(is_junction):
        try:
            if is_junction():
                return True
        except OSError:
            return True

    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    if reparse_flag:
        try:
            attributes = getattr(path.stat(follow_symlinks=False), "st_file_attributes", 0)
            if attributes & reparse_flag:
                return True
        except (FileNotFoundError, OSError):
            pass
    return False


def _reject_symlink_components(root: Path, candidate: Path) -> None:
    root = root.resolve()
    try:
        relative = candidate.absolute().relative_to(root)
    except ValueError as exc:
        raise UnsafePathError("path is outside workspace") from exc
    cursor = root
    if cursor.exists() and is_link_or_reparse(cursor):
        raise UnsafePathError(f"symlink/reparse-style workspace root is not allowed: {cursor}")
    for part in relative.parts:
        cursor = cursor / part
        if cursor.exists() and is_link_or_reparse(cursor):
            raise UnsafePathError(f"symlink/reparse-style path component is not allowed: {cursor}")


def safe_path(root: Path | str, candidate: Path | str) -> Path:
    root_path = Path(root).resolve()
    raw = Path(candidate)
    if not raw.is_absolute():
        raw = root_path / raw
    _reject_symlink_components(root_path, raw)
    resolved = raw.resolve(strict=False)
    try:
        resolved.relative_to(root_path)
    except ValueError as exc:
        raise UnsafePathError(f"path escapes workspace: {candidate}") from exc
    return resolved


def iter_project_files(root: Path | str) -> Iterable[Path]:
    root_path = Path(root).resolve()
    if not root_path.is_dir():
        return
    for current_raw, directories, filenames in os.walk(root_path, topdown=True, followlinks=False):
        current = Path(current_raw)
        kept_directories: list[str] = []
        for name in sorted(directories):
            candidate = current / name
            try:
                relative = candidate.relative_to(root_path)
            except ValueError:
                continue
            if any(part in EXCLUDED_DIRS for part in relative.parts):
                continue
            if is_link_or_reparse(candidate):
                continue
            kept_directories.append(name)
        directories[:] = kept_directories
        for name in sorted(filenames):
            path = current / name
            try:
                relative = path.relative_to(root_path)
            except ValueError:
                continue
            if any(part in EXCLUDED_DIRS for part in relative.parts):
                continue
            if is_link_or_reparse(path):
                continue
            if path.is_file():
                yield path


def classify_file(root: Path | str, path: Path | str) -> FileClassification:
    root_path = Path(root).resolve()
    file_path = safe_path(root_path, path)
    relative = file_path.relative_to(root_path).as_posix()
    protected = is_secret_path(file_path)
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
