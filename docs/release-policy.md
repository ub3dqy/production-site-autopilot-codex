# Release policy

- `VERSION` is the release version source.
- Beta releases may publish with live evidence `NOT_RUN`, but must state it.
- Stable releases require `PASS` for all evidence marked `required_for_stable`.
- Archives are deterministic and rebuilt in CI.
- Release output includes `SHA256SUMS`, `test-evidence.json`, `sbom.cdx.json`, and `provenance.json`.
- Generated archives are not committed to the source tree.
- `main` is updated through reviewed pull requests; release tooling never force-pushes it.
