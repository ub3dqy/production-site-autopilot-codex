from __future__ import annotations

import argparse
import json
from pathlib import Path

from .detect import detect
from .doctor import run_doctor
from .models import Mode, ProductionProfile
from .policy import evaluate
from .reports import validate_report, write_report
from .snapshot import SnapshotManager


def _json(value: object) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="production-site-autopilot")
    parser.add_argument("--version", action="version", version="7.2.0-beta.1")
    sub = parser.add_subparsers(dest="command", required=True)
    doctor = sub.add_parser("doctor")
    doctor.add_argument("path", nargs="?", default=".")
    detector = sub.add_parser("detect")
    detector.add_argument("path", nargs="?", default=".")
    detector.add_argument("--mode", choices=[item.value for item in Mode])
    policy = sub.add_parser("policy")
    policy.add_argument("action")
    policy.add_argument("--mode", default=Mode.ADOPTION.value, choices=[item.value for item in Mode])
    policy.add_argument("--profile", default=ProductionProfile.MARKETING_SITE.value, choices=[item.value for item in ProductionProfile])
    policy.add_argument("--approved", action="append", default=[])
    policy.add_argument("--outside-workspace", action="store_true")
    policy.add_argument("--carries-secret", action="store_true")
    policy.add_argument("--external", action="store_true")
    snapshot = sub.add_parser("snapshot")
    snapshot.add_argument("path", nargs="?", default=".")
    snapshot.add_argument("--run-id")
    finalize = sub.add_parser("finalize")
    finalize.add_argument("run_id")
    finalize.add_argument("path", nargs="?", default=".")
    rollback = sub.add_parser("rollback")
    rollback.add_argument("run_id")
    rollback.add_argument("path", nargs="?", default=".")
    rollback.add_argument("--force", action="store_true")
    validate = sub.add_parser("validate-report")
    validate.add_argument("report")
    report = sub.add_parser("write-report")
    report.add_argument("input")
    report.add_argument("path", nargs="?", default=".")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "doctor":
        _json(run_doctor(args.path)); return 0
    if args.command == "detect":
        requested = Mode(args.mode) if args.mode else None
        _json(detect(args.path, requested_mode=requested).to_dict()); return 0
    if args.command == "policy":
        result = evaluate(
            args.action,
            mode=Mode(args.mode),
            profile=ProductionProfile(args.profile),
            owner_approved=args.approved,
            target_within_workspace=not args.outside_workspace,
            carries_secret=args.carries_secret,
            external_destination=args.external,
        )
        _json(result.to_dict()); return 0 if result.decision.value == "ALLOW" else 2
    if args.command == "snapshot":
        _json(SnapshotManager(args.path).create(args.run_id)); return 0
    if args.command == "finalize":
        _json(SnapshotManager(args.path).finalize(args.run_id)); return 0
    if args.command == "rollback":
        _json(SnapshotManager(args.path).rollback(args.run_id, force=args.force)); return 0
    if args.command == "validate-report":
        data = json.loads(Path(args.report).read_text(encoding="utf-8"))
        errors = validate_report(data); _json({"valid": not errors, "errors": errors}); return 0 if not errors else 1
    if args.command == "write-report":
        data = json.loads(Path(args.input).read_text(encoding="utf-8")); _json(write_report(args.path, data)); return 0
    return 2
