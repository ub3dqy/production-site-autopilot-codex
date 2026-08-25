from __future__ import annotations

import json
from pathlib import Path

from .models import DetectionResult, Mode, Stack
from .security import iter_project_files


def _read_package_json(root: Path) -> dict:
    path = root / "package.json"
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def detect_stack(root: Path | str) -> tuple[Stack, ...]:
    root_path = Path(root).resolve()
    stacks: list[Stack] = []
    package = _read_package_json(root_path)
    dependencies: dict = {}
    for key in ("dependencies", "devDependencies", "peerDependencies"):
        value = package.get(key, {})
        if isinstance(value, dict):
            dependencies.update(value)
    if (root_path / "wp-config.php").exists() or (root_path / "wp-content").is_dir():
        stacks.append(Stack.WORDPRESS)
    if any(root_path.glob("astro.config.*")) or "astro" in dependencies:
        stacks.append(Stack.ASTRO)
    if any(root_path.glob("next.config.*")) or "next" in dependencies:
        stacks.append(Stack.NEXTJS)
    if any(root_path.glob("vite.config.*")) or ("vite" in dependencies and "react" in dependencies):
        stacks.append(Stack.REACT_VITE)
    if package and not any(item in stacks for item in (Stack.ASTRO, Stack.NEXTJS, Stack.REACT_VITE)):
        stacks.append(Stack.NODE)
    if (root_path / "pyproject.toml").is_file() or (root_path / "requirements.txt").is_file():
        stacks.append(Stack.PYTHON)
    if (root_path / "composer.json").is_file():
        stacks.append(Stack.PHP)
    if list(root_path.glob("*.html")) and not stacks:
        stacks.append(Stack.STATIC)
    return tuple(dict.fromkeys(stacks)) or (Stack.UNKNOWN,)


def detect(root: Path | str, *, requested_mode: Mode | None = None, confidence_threshold: float = 0.70) -> DetectionResult:
    root_path = Path(root).resolve()
    reasons: list[str] = []
    files = list(iter_project_files(root_path))
    if requested_mode is not None:
        mode = requested_mode
        confidence = 1.0
        reasons.append("mode explicitly requested by owner")
    elif not files:
        mode = Mode.GREENFIELD
        confidence = 0.95
        reasons.append("workspace has no project files")
    elif (root_path / ".production-site" / "migration.json").is_file():
        mode = Mode.MIGRATION
        confidence = 0.90
        reasons.append("migration contract detected")
    elif any((root_path / name).exists() for name in ("package.json", "pyproject.toml", "composer.json", "index.html", "wp-config.php")):
        mode = Mode.ADOPTION
        confidence = 0.88
        reasons.append("existing site/application markers detected")
    else:
        mode = Mode.AUDIT
        confidence = 0.45
        reasons.append("project type is ambiguous")
    stacks = detect_stack(root_path)
    if stacks == (Stack.UNKNOWN,) and mode is not Mode.GREENFIELD:
        confidence = min(confidence, 0.60)
        reasons.append("stack could not be identified")
    elif stacks == (Stack.UNKNOWN,):
        reasons.append("stack will be selected during greenfield planning")
    mutation_allowed = mode is not Mode.AUDIT and confidence >= confidence_threshold
    if not mutation_allowed and mode is not Mode.AUDIT:
        reasons.append("confidence below threshold; falling back to audit-only")
        mode = Mode.AUDIT
    return DetectionResult(mode, stacks, confidence, mutation_allowed, tuple(reasons))
