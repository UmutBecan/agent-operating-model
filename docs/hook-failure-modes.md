# Hook failure modes and how this hook handles them

A hook is only a control if it fails safely. These are the failure patterns that show up repeatedly in public agent-tool issue trackers (measured 2026-10-28, see the gap analysis) and what this example does about each.

| Failure mode | What goes wrong | What this hook does | Test |
|---|---|---|---|
| Hook crashes or its input is malformed | The action may proceed as if no hook existed | Every error exits 2 (block) | `test_bad_input_fails_closed` |
| Policy file missing or invalid | Silent allow | Exit 2 | `test_missing_policy_fails_closed` |
| Wrapped commands (`bash -c "..."`, `sudo`, `powershell -Command`) | The outer command looks harmless | The inner command is judged | `Wrappers` in `test_hook_extra.py` |
| Chained commands, including a single `&` (cmd) | Only the first command is checked | Highest tier of all parts wins; `2>&1` is not a separator | `Wrappers` |
| Windows commands and backslash paths | Unix-only rules miss `Remove-Item -Recurse -Force`, `rd /s`, `type .env` | Windows patterns in `policy.json`; paths normalised to `/` | `WindowsCommands`, `FileWrites` |
| File edits bypass a Bash-only hook | `Write`/`Edit` can change `.env` or CI files directly | `protected_paths` (ask) and `blocked_paths` (block) for Write/Edit/MultiEdit/NotebookEdit | `FileWrites` |
| Nothing records what was decided | No evidence after an incident | Tier 1, 2 and 3 decisions go to the hash-chained log when `AUDIT_LOG` is set | `AuditOfEveryDecision` |
| The agent edits its own rules | The gate is removed by the thing it gates | `hooks/policy.json` and `CLAUDE.md` are protected paths (ask) | `FileWrites` |

## Not covered (known limits)
- Obfuscated commands (encoded payloads, variables built at runtime) are not understood; unknown commands are tier 2 (ask), which is the fail-closed default, not a guarantee.
- The hook cannot see what a script it allows does internally.
- It is not a sandbox. Use OS permissions, a non-admin account and branch protection as well.
- Hook configuration formats change between Claude Code versions; check the current documentation. Matcher to use for the extended hook: `Bash|PowerShell|Write|Edit|MultiEdit|NotebookEdit` (verify the tool names in your version).
