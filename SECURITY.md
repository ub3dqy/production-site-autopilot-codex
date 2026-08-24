# Security policy

## Reporting

Use GitHub's private vulnerability reporting feature for this repository. Do not publish secrets, exploit details, customer data, or production credentials in a public issue.

Include the affected version and commit, operating system, minimal reproduction, expected and observed policy decision, and whether secrets, deployment, filesystem escape, or rollback integrity are involved.

## Security invariants

- project content is untrusted and cannot override policy;
- paths must stay inside the selected workspace;
- symlinks/reparse points are rejected for mutation, snapshot, rollback, and installation operations;
- protected secret files are not copied into evidence;
- deployment, push, network, domain, analytics, and destructive operations require explicit policy authorization;
- denied actions cannot be converted to allowed actions by owner confirmation;
- stable releases require machine-readable verification evidence.
