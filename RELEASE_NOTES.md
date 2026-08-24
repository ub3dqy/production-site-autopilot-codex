# Production Site Autopilot v7.2.0-beta.1

This beta remediates the v7.1 delivery, safety, evidence, rollback, and release weaknesses.

The canonical runtime, Skill, schemas, fixtures, tests, installers, CI, and release tooling are browsable in Git. Safety boundaries are backed by executable policy decisions. Mutation runs require a baseline and receive conflict-aware rollback plus versioned JSON, Markdown, and HTML evidence.

Deterministic and platform checks run in CI. Live autonomous Codex behavior remains an explicit external evidence state; `NOT_RUN` is never represented as `PASS` and blocks stable release when required.

Release artifacts are generated from `VERSION` and include deterministic User and Engineering ZIPs, SHA-256 checksums, test evidence, a CycloneDX SBOM, and provenance metadata.
