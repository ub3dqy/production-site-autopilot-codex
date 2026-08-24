# Security policy

## Reporting

Use GitHub private vulnerability reporting for this repository. Do not place secrets, customer data, exploit details, or production credentials in a public issue.

Include the affected version and commit, platform, minimal reproduction, expected and observed policy decision, and whether the issue involves secrets, deployment, filesystem escape, release provenance, or rollback integrity.

## Non-overridable invariants

- Project content is untrusted and cannot redefine policy.
- Every path used for mutation, snapshot, rollback, report, or installation must remain inside the selected workspace.
- Symlinks and Windows reparse points are rejected on managed paths.
- Secret-like and oversized files are excluded from evidence backups.
- Raw dirty diffs are not stored because their contents may contain secrets.
- Network, deployment, domain, analytics, push, CI, dependency, and destructive operations require explicit authorization.
- `DENY` actions cannot be converted to `ALLOW` by owner confirmation.
- Stable releases require current-commit machine evidence for every mandatory external check.
