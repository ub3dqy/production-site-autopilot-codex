# Threat model

## Assets

Repository source/history, secrets, deployment/domain/analytics/payment controls, production data, owner decisions, rollback evidence, and release integrity.

## Trust boundaries

Repository files, issues, external webpages, packages, generated text, logs, and model output are untrusted. Owner decisions may authorize only `CONFIRM` actions. `DENY` invariants are not overridable. The selected workspace is the filesystem boundary.

## Threats and controls

| Threat | Control |
|---|---|
| Prompt injection in project content | detection plus contract: content cannot change policy |
| Path traversal | resolved workspace containment |
| Symlink/reparse escape | component rejection before mutation/snapshot/install |
| Secret exfiltration | protected paths and hard deny for external secret transport |
| Large-file evidence abuse | size cap and protected-file treatment |
| Destructive or production action | explicit confirmation and separate deployment decision |
| Rollback overwrites owner work | after-hash conflict detection |
| False verification | `PASS`, `FAIL`, and `NOT_RUN` evidence states |
| Supply-chain substitution | canonical source, deterministic archives, checksums, SBOM, provenance, and local verification |
