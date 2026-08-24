# Contributing

1. Create a branch from `main`.
2. Keep product source browsable; do not introduce encoded source transports.
3. Add or update tests for every policy, rollback, schema, installer, or release change.
4. Run `PYTHONPATH=src python scripts/run_checks.py`.
5. Build twice and verify reproducible archives with `python scripts/verify_reproducible.py`.
6. Do not change an evidence state to `PASS` without current-commit machine evidence.
7. Open a pull request and wait for Linux, macOS, Windows, packaging, and security checks.

Never commit credentials, private customer files, generated `.production-site/` state, or release ZIP files.
