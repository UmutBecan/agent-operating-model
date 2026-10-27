# agent-operating-model

> A copy-and-edit operating model for working with a team of AI agents: roles, cost modes, a decision register, evidence rules and approval gates. Built from one person's daily use, written the way an IT operations team would run it.

You do not need a framework. You need a few files the agents read every session and a few habits you keep. This repository gives you both.

## 60 seconds

```bash
git clone https://github.com/UmutBecan/agent-operating-model
cp -r agent-operating-model/templates/* /path/to/your/project/
python3 agent-operating-model/scripts/decision_age.py agent-operating-model/templates/decision-register.md
```

Then edit `CLAUDE.md` (or your agent's instruction file): set the owner, the language, the gates that only you may pass. The register script prints how old every open decision is, so nothing you have not answered disappears.

## What is inside

| Path | What it is |
|---|---|
| `templates/CLAUDE.md` | Project instructions: owner, roles, cost modes, evidence rule, gates. Edit the placeholders. |
| `templates/decision-register.md` | Open decisions with age and status. Carried into every report. |
| `templates/report-format.md` | A short status report: BLUF, RAG, KPIs, RAID, decisions needed. |
| `templates/approval-gates.md` | Which actions need a human, every time. A checklist, not a policy essay. |
| `templates/command-tiers.md` | Four tiers for commands (free, logged, ask, blocked) with a fail-closed default. |
| `templates/definition-of-done.md` | A done-checklist tied to command output, not to the agent's opinion. |
| `templates/protected-paths.md` | What an agent may read but not change without a gate, and how to enforce it. |
| `templates/agents/` | Three role files to start from: coordinator, skeptic, verifier. |
| `scripts/decision_age.py` | Prints the age of each open decision. Python 3, no dependencies. |
| `scripts/audit_chain.py` | A tamper-evident action log: each entry hashes the one before. Python 3, no dependencies. |
| `tests/` | Tests for both scripts: `python3 -m unittest discover -s tests`. |
| `docs/failure-log.md` | The failures that created each rule. |
| `docs/prior-art.md` | Related projects, what this takes as an idea, what they do better. |

## Principles

1. **Separate who, how and what is true.** Roles say who does the work. Procedures say how. Documents hold facts. Mixing them makes each worse.
2. **One point of contact.** You talk to one coordinating role. It routes work and decides what runs in parallel.
3. **A register, not memory.** Every open question has an age and a status.
4. **Cost modes.** Economy by default; deeper only when risk justifies it.
5. **Evidence before claims.** No agent says 'done' without the output that shows it.
6. **Gates only a human passes.** Release, visual sign-off and anything outward-facing.
7. **Deterministic where it matters.** Checks and scores are rules, not guesses by a model.

## Who this is for

One person or a small team who run several projects with AI agents and want the discipline of an operations team without the overhead. It shows how the habits work; it does not claim to scale to a company.

## Limits

- It is a one-person system today. Team use needs ownership and access rules this repository does not define.
- Agents make mistakes. Most rules here exist because of a real failure (see `docs/failure-log.md`).
- The value is the discipline, not the tooling.

## License

MIT. See `LICENSE`.
