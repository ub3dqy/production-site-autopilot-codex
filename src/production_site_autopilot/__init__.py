"""Production Site Autopilot runtime."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from .models import DetectionResult, Mode, PolicyDecision, PolicyResult, ProductionProfile, RunStatus, Stack

try:
    __version__ = version("production-site-autopilot")
except PackageNotFoundError:
    version_file = Path(__file__).resolve().parents[2] / "VERSION"
    __version__ = version_file.read_text(encoding="utf-8").strip() if version_file.is_file() else "0+unknown"

__all__ = [
    "DetectionResult",
    "Mode",
    "PolicyDecision",
    "PolicyResult",
    "ProductionProfile",
    "RunStatus",
    "Stack",
    "__version__",
]
