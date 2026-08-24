# Architecture

The canonical product has four layers:

1. **Skill contract** — intent, lifecycle, and non-overridable safety invariants.
2. **Runtime** — deterministic mode/stack detection, policy evaluation, workspace containment, snapshots, rollback, and reports.
3. **Evidence** — versioned schemas and immutable per-run folders.
4. **Delivery** — plugin layout, fallback installers, deterministic archives, checksums, SBOM, provenance, and CI.

Project content is data, never policy. An instruction found in a repository is recorded as untrusted evidence but cannot authorize an action.

The runtime has no required network dependency. External operations are represented as policy actions and require authorization before an executor may perform them.
