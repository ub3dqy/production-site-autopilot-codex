# Production Site Autopilot v7.2.0-beta.1 — GitHub distribution

This branch is the Git-native distribution surface for the verified beta. It does not depend on GitHub Actions.

## Direct GitHub downloads

- [User Edition ZIP](https://github.com/ub3dqy/production-site-autopilot-codex/archive/refs/heads/release/user-v7.2.0-beta.1.zip)
- [Engineering Edition ZIP](https://github.com/ub3dqy/production-site-autopilot-codex/archive/refs/heads/release/engineering-v7.2.0-beta.1.zip)
- [Complete GitHub bundle ZIP](https://github.com/ub3dqy/production-site-autopilot-codex/archive/refs/heads/release/bundle-v7.2.0-beta.1.zip)

The complete bundle contains expanded User and Engineering editions plus release notes, local verification evidence, test evidence, SBOM, provenance, and artifact checksums.

## Source identity

- Verified source commit: `1d4ec66c54882a9ed023850249fada103f7d4fb1`
- User distribution commit: `a0d9255165b6aed461abc026f9443c46a2dc3bbb`
- Version: `7.2.0-beta.1`
- Release class: **beta / prerelease**, not stable

## Verification

- Repository integrity: PASS
- Unit tests: 26/26 PASS
- Python compilation: PASS
- POSIX install, doctor, bundled runtime, and uninstall: PASS
- Deterministic double release build: PASS
- Native Windows runtime: NOT_RUN
- Live autonomous Codex suite: NOT_RUN
- Stable eligibility: BLOCKED by design

GitHub-generated branch archives are distribution containers and therefore do not have the same bytes as the deterministic locally built archives referenced in `SHA256SUMS`. The expanded source trees are derived from the exact commits listed above.
