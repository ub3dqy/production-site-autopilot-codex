# Production Site Autopilot v7.2.0-beta.1 — official GitHub prerelease

This is the official GitHub prerelease distribution for the verified beta. It does not depend on GitHub Actions.

## Direct downloads

- [Prerelease page](https://github.com/ub3dqy/production-site-autopilot-codex/releases/tag/v7.2.0-beta.1)
- [User Edition ZIP](https://github.com/ub3dqy/production-site-autopilot-codex/releases/download/v7.2.0-beta.1/production-site-autopilot-codex-user-v7.2.0-beta.1.zip)
- [Engineering Edition ZIP](https://github.com/ub3dqy/production-site-autopilot-codex/releases/download/v7.2.0-beta.1/production-site-autopilot-codex-engineering-v7.2.0-beta.1.zip)
- [Complete release bundle ZIP](https://github.com/ub3dqy/production-site-autopilot-codex/releases/download/v7.2.0-beta.1/production-site-autopilot-codex-v7.2.0-beta.1-release-bundle.zip)

The complete bundle contains User and Engineering editions plus release notes, local verification evidence, deterministic test evidence, SBOM, provenance, final status, and checksums.

## Source identity

- Verified product source commit: `1d4ec66c54882a9ed023850249fada103f7d4fb1`
- Release tag: `v7.2.0-beta.1` → exact verified source commit
- Publication metadata commit: `0df136d605d15369d0c7f908d793813f818475f8`
- Version: `7.2.0-beta.1`
- Release class: **beta / prerelease**, not stable

## Artifact integrity

- User Edition SHA-256: `4c02b7a7ef2be799a5f1c21e35f6c018e11f689f1b5fc511835be0ed2b30cfc1`
- Engineering Edition SHA-256: `f0b5d3e72ca3c96e0b4cc73f07b722e492170bbca99773703462e24eb1929534`
- Complete bundle SHA-256: `2fdccb6a3a73f7197df412e6fea72aab17b4d1aad92639bd7e99b2b047bfd81d`

All release assets were downloaded back after upload and verified byte-for-byte. GitHub also records a SHA-256 digest for each uploaded asset.

## Verification

- Repository integrity: PASS
- Unit tests: 26/26 PASS
- Python compilation: PASS
- POSIX install, doctor, bundled runtime, and uninstall: PASS
- Deterministic double release build: PASS
- Native Windows runtime: NOT_RUN
- Live autonomous Codex suite: NOT_RUN
- Stable eligibility: BLOCKED by design

## Repository administration

- `main` branch protection: enabled
- changes through pull requests: required
- force pushes: blocked
- branch deletion: blocked
- conversation resolution: required
- GitHub Actions required checks: none

No unexecuted check has been represented as PASS, and the beta evidence cannot be reused for a future stable candidate without re-verification against that candidate's exact commit.
