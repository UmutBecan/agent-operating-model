# Intake checklist for third-party skills, plugins and MCP servers

Before an agent is allowed to load a skill, plugin, hook pack or MCP server from outside your team, a human answers these. It takes about ten minutes and is a gate in the sense of `approval-gates.md`.

1. **Source and license.** Where does it come from? Is there a license file you can read? (No license means no permission to reuse. GPL/AGPL needs legal review before it goes near proprietary code.)
2. **Pin it.** Record the exact version or commit. Do not track `latest`.
3. **Read what it can do.** Open the instruction file (for example `SKILL.md`) and any scripts. List the commands it runs, the files it writes and the network it calls.
4. **Permissions.** Which tools does it ask for? Give the least. For an MCP server: which credentials, which scopes, read-only first.
5. **Secrets.** Does it read environment variables or key files? It should not need yours.
6. **Hooks and background actions.** Does it install hooks or run on session start? Treat that as code execution on your machine.
7. **Windows and Linux.** Does it assume one shell or path style? Test on the OS you use before relying on it.
8. **Cost.** Does it add large context or many calls? Estimate the token cost of one typical use.
9. **Rollback.** How do you remove it, and what does it leave behind?
10. **Record it.** One line in the decision register: what, version, who approved, date.

Supply-chain incidents in tools agents depend on are real (a compromised package release in a widely used LLM library was reported in a public issue on 2026-10-21); pinning and review are the cheap defence. This checklist is a starting point, not a certification.
