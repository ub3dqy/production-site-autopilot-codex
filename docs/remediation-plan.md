# Production Site Autopilot v7.2 remediation

This branch converts the repository from an opaque transport-first release into a browsable, reproducible, testable product.

## Required outcomes

- Canonical Engineering source and generated User Edition are reviewable in Git.
- Release claims are generated from machine-readable evidence, not copied counters.
- Windows, Linux, deterministic, security-boundary, rollback, and report-schema checks run in CI.
- Live Codex behavior is represented honestly as `PASS`, `FAIL`, or `NOT_RUN`; stable releases cannot silently treat `NOT_RUN` as success.
- Safety decisions are enforced by an executable `ALLOW` / `CONFIRM` / `DENY` policy layer.
- Every mutation run records a baseline, evidence, history, residual risks, and a verified rollback path.
- Version values come from one source of truth.
- Releases include checksums, test evidence, SBOM, and provenance.
- The repository is self-contained and does not depend on source fragments from another repository.
- User installation has a native Codex-plugin layout plus explicit fallback installers.

The implementation preserves the verified v7.1.0 behavior while replacing its delivery and lifecycle weaknesses.