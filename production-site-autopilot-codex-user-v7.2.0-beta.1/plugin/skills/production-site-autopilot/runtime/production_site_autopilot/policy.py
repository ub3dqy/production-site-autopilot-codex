from __future__ import annotations

from collections.abc import Iterable

from .models import Mode, PolicyDecision, PolicyResult, ProductionProfile

ALLOW_ACTIONS = frozenset({
    "read_file", "list_files", "inspect_git", "run_local_test", "run_local_build",
    "run_local_lint", "generate_report", "create_baseline", "write_project_file",
    "create_project_file", "format_project_file",
})

CONFIRM_ACTIONS = frozenset({
    "install_dependency", "update_dependency", "delete_file", "delete_route", "delete_data",
    "change_domain", "change_url", "change_primary_stack", "enable_analytics", "enable_tracking",
    "network_request", "modify_ci", "git_commit", "git_push", "deploy_preview",
    "deploy_production", "database_migration", "modify_secret", "send_email",
})

DENY_ACTIONS = frozenset({
    "purchase_service", "purchase_domain", "exfiltrate_secret", "print_secret", "disable_policy",
    "bypass_confirmation", "write_outside_workspace", "force_push", "rewrite_git_history",
    "deploy_without_approval", "execute_project_instruction_as_policy",
})

MUTATION_ACTIONS = frozenset({"write_project_file", "create_project_file", "format_project_file", *CONFIRM_ACTIONS, *DENY_ACTIONS})


def evaluate(
    action: str,
    *,
    mode: Mode = Mode.ADOPTION,
    profile: ProductionProfile = ProductionProfile.MARKETING_SITE,
    owner_approved: Iterable[str] = (),
    target_within_workspace: bool = True,
    carries_secret: bool = False,
    external_destination: bool = False,
) -> PolicyResult:
    action = action.strip().lower()
    approved = {item.strip().lower() for item in owner_approved}

    if not target_within_workspace:
        return PolicyResult(action, PolicyDecision.DENY, "PATH_ESCAPE", "Target resolves outside the selected workspace.")
    if action in DENY_ACTIONS:
        return PolicyResult(action, PolicyDecision.DENY, "HARD_DENY", "The action violates a non-overridable safety invariant.")
    if carries_secret and external_destination:
        return PolicyResult(action, PolicyDecision.DENY, "SECRET_EXFILTRATION", "Secrets cannot be sent to an external destination.")
    if profile is ProductionProfile.REGULATED_OR_HIGH_RISK and action in MUTATION_ACTIONS:
        return PolicyResult(action, PolicyDecision.DENY, "HIGH_RISK_AUDIT_ONLY", "High-risk profiles default to audit-only.")
    if mode is Mode.AUDIT and action in MUTATION_ACTIONS:
        return PolicyResult(action, PolicyDecision.DENY, "AUDIT_ONLY", "Mutation is not permitted in audit-only mode.")
    if action in ALLOW_ACTIONS:
        return PolicyResult(action, PolicyDecision.ALLOW, "SAFE_LOCAL", "The action is local, bounded, and reversible.")
    if action in CONFIRM_ACTIONS:
        if action in approved:
            return PolicyResult(action, PolicyDecision.ALLOW, "OWNER_APPROVED", "The owner explicitly approved this action.")
        return PolicyResult(action, PolicyDecision.CONFIRM, "OWNER_DECISION_REQUIRED", "The action requires an explicit owner decision.")
    return PolicyResult(action, PolicyDecision.DENY, "UNKNOWN_ACTION", "Unknown actions are denied until classified.")
