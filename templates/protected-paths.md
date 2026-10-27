# Protected paths and branches

Things an agent may read but not change without the owner's gate. Enforce them with branch protection, file permissions or a pre-commit check, not with a polite instruction.

| Protected | Why | How to enforce |
|---|---|---|
| `main` / release branches | A direct change skips review | Branch protection; agents work on feature branches |
| Applied database migrations | They are history; a change must be a new migration | Test that pins their hashes |
| Secrets and key files | Exposure is not reversible | Deny-list in the agent's permissions; secret scan in CI |
| Test files that exist | Tests must not shrink to make a change pass | Rule: extend or add a companion file; test count may not drop without a written reason |
| This operating model's own rules | An agent must not edit the rules it is held to | Read-only mount or an owner-only review |
| Production configuration | Changes affect real users | Gate in `approval-gates.md` |

Everything else is open to the agent, on a feature branch, with the evidence rule applied.
