# Release policy

- `VERSION` is the release version source.
- Canonical verification is local and runs through `scripts/verify_local.py`; GitHub Actions are not required or used as a release gate.
- Beta releases may publish with native Windows or live Codex evidence `NOT_RUN`, but must state it.
- Stable releases require `PASS` for every evidence file marked `required_for_stable`, and each `PASS` must reference the exact source commit.
- Archives are deterministic and must be built twice locally with identical SHA-256 hashes.
- Release output includes `SHA256SUMS`, `test-evidence.json`, `local-verification.json`, `sbom.cdx.json`, and `provenance.json`.
- Generated archives are not committed to the source tree.
- `main` is updated through reviewed pull requests; release tooling never force-pushes it.
