# Canonical local verification

GitHub Actions are unavailable for this repository and are not part of the trust chain. All mandatory checks and beta release artifacts are produced locally.

## Windows

```cmd
VERIFY_LOCAL_WINDOWS.cmd --source-commit <40-character-commit>
```

On native Windows the verifier also runs the PowerShell installer lifecycle and updates `evidence/windows-native.json` only after a real PASS.

## macOS or Linux

```bash
./VERIFY_LOCAL.sh --source-commit <40-character-commit>
```

## What the verifier does

1. validates repository structure and version consistency;
2. runs the complete `unittest` suite and Python compilation;
3. exercises the POSIX installer lifecycle where applicable;
4. builds User and Engineering archives twice;
5. compares archive SHA-256 values and validates internal manifests;
6. validates `SHA256SUMS`;
7. writes release artifacts and machine-readable evidence to `dist/` and `build/`.

`live Codex` and `native Windows` remain independent evidence states. `NOT_RUN` is allowed for a beta but blocks a stable release. A stale PASS from another commit is treated as FAIL for stable eligibility.
