from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class Mode(str, Enum):
    GREENFIELD = "greenfield"
    ADOPTION = "adoption"
    AUDIT = "audit"
    REDESIGN = "redesign"
    MIGRATION = "migration"


class Stack(str, Enum):
    STATIC = "static"
    ASTRO = "astro"
    NEXTJS = "nextjs"
    REACT_VITE = "react-vite"
    NODE = "node"
    PYTHON = "python"
    PHP = "php"
    WORDPRESS = "wordpress"
    UNKNOWN = "unknown"


class PolicyDecision(str, Enum):
    ALLOW = "ALLOW"
    CONFIRM = "CONFIRM"
    DENY = "DENY"


class ProductionProfile(str, Enum):
    MARKETING_SITE = "MARKETING_SITE"
    WEB_APPLICATION = "WEB_APPLICATION"
    COMMERCE = "COMMERCE"
    REGULATED_OR_HIGH_RISK = "REGULATED_OR_HIGH_RISK"


class RunStatus(str, Enum):
    AUDIT_COMPLETE = "AUDIT_COMPLETE"
    READY_FOR_REVIEW = "READY_FOR_REVIEW"
    READY_FOR_PREVIEW = "READY_FOR_PREVIEW"
    READY_FOR_DEPLOYMENT = "READY_FOR_DEPLOYMENT"
    READY_WITH_DEFERRED_ITEMS = "READY_WITH_DEFERRED_ITEMS"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class DetectionResult:
    mode: Mode
    stacks: tuple[Stack, ...]
    confidence: float
    mutation_allowed: bool
    reasons: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["mode"] = self.mode.value
        data["stacks"] = [item.value for item in self.stacks]
        return data


@dataclass(frozen=True)
class PolicyResult:
    action: str
    decision: PolicyDecision
    code: str
    reason: str

    def to_dict(self) -> dict[str, str]:
        return {"action": self.action, "decision": self.decision.value, "code": self.code, "reason": self.reason}


@dataclass
class DecisionItem:
    id: str
    question: str
    options: list[str]
    default: str | None = None
    blocks: list[str] = field(default_factory=list)


@dataclass
class DecisionPacket:
    checkpoint: str
    items: list[DecisionItem]
    independent_work_continues: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
