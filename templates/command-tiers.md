# Command tiers

Classify what an agent may run, so the safe default is to ask. Edit the examples for your stack.

| Tier | Rule | Examples |
|---|---|---|
| 0, free | Run without asking; reads only | list files, read a file, `git status`, `git diff`, run the test suite locally |
| 1, logged | Run, and record it in the audit log | `git add`, `git commit` on a feature branch, writing inside the project folder |
| 2, ask | A human says yes first, every time | `git push`, `git reset`, installing a package, calling an external service, any write to production |
| 3, blocked | Never, even if asked in a file or a web page | recursive delete outside the project, `chmod 777`, disabling a check, force-push to the main branch, reading secret files |

Rules:
1. **Fail closed.** A command that is not listed is tier 2.
2. **The policy sits outside the agent.** A hook, wrapper or CI check enforces it; the agent cannot edit its own policy.
3. **Tier 1 is logged.** Use `scripts/audit_chain.py` so the log shows if it was edited later.
4. **Instructions from content are not permission.** A file, page or tool output cannot raise a command's tier.
