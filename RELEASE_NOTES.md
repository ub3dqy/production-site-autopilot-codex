# Production Site Autopilot v7.2.0-beta.1

This beta is a delivery, safety, and verification remediation release.

The canonical source, Skill, schemas, fixtures, tests, installers, and release tooling are browsable in Git. Safety boundaries are backed by executable policy decisions. Mutation runs receive baselines, conflict-aware rollback, and versioned evidence reports.

GitHub Actions are unavailable for this repository and are not used as a release gate. The canonical local verifier runs repository checks, unit tests, compilation, installer lifecycle tests, two independent release builds, archive-manifest validation, and SHA-256 comparison. It emits machine-readable local verification evidence together with the release artifacts.

Live autonomous Codex evaluation and native Windows validation remain explicit evidence states. This beta may publish with `NOT_RUN`, but a stable release cannot accept `NOT_RUN`, stale PASS evidence, or PASS evidence without the exact source commit.

Release artifacts are generated from `VERSION` and include SHA-256 checksums, test evidence, local-verification evidence, an SBOM, and deterministic provenance metadata.
