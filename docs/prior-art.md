# Prior art and what this repository adds

Other projects solve parts of this problem. Their ideas shaped some templates here; the text and code in this repository are written independently. Check each project's own licence before reusing its code.

| Project | What it does well | What this repository takes as an idea | Note |
|---|---|---|---|
| l'Agence (agent shell with command gating) | Tiers for commands, fail-closed default, a tamper-evident decision ledger, CI guard | `templates/command-tiers.md`, `scripts/audit_chain.py` (own implementation) | Licence is MIT with a Commons Clause: not copied |
| Decapod (governance runtime for coding agents) | Intent and scope before action, completion tied to verification output, protected paths, repo-native state | `templates/definition-of-done.md`, `templates/protected-paths.md` | Licence not stated on the page I read: ideas only |
| Subagent collections (for example VoltAgent's list) | A large library of ready roles in a consistent file format | `templates/agents/` uses the same simple role-file idea, with boundaries and escalation | Collections give roles; they do not give an operating model |
| Chock (governance-as-code for coding agents) | Rules compiled into git hooks, CI gates and native pre-execution hooks | `hooks/` shows the same idea in one small file | Not copied |
| handrail (declarative guardrails, MIT) | Rule files in tiers across agent harnesses | The tier-file idea in `hooks/policy.json` | Different language; idea only |
| TaG (spending, credentials, deployment guardrails) | Cross-project isolation | none | Business Source License: source-available, not reused |
| General human-in-the-loop guidance | Why approval gates and separation of duties matter | `templates/approval-gates.md` turns the theory into a checklist | Mostly articles, not repositories |

## What is different here

- **Operating model first, tooling second.** Roles, a decision register with ages, cost modes, a report format and gates work together, in plain files.
- **Honesty rules** (no invented data, unknown stays unknown, dated results) and a log of the failures that created each rule.
- **Works with any agent.** No runtime to install; the discipline lives in files and small scripts.

## What others do better

- Real enforcement (hooks, sandboxes, CI actions) is stronger in the projects above. This repository describes the policy and gives a log tool; it does not ship an enforcer.
- Larger role libraries and multi-agent orchestration are outside this repository's scope.
