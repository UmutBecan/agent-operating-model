# Variant: infrastructure

Append to `CLAUDE.md`.

## Rules
- **Preview before apply.** Show the plan (`terraform plan`, `ansible --check --diff`) and wait for a yes.
- **One writable source of truth** for documentation and configuration. Copies are read-only.
- **A backup is real after a restore test.** Report the restore result, not just the backup job.
- Edit single points of failure (SSH keys, firewall rules, the network bridge) one change at a time, with a second session open.
- Production writes, deletions and network changes are gates in `approval-gates.md`.

## Evidence
Verify live state with a command before trusting any document's status line, including this repository's own.
