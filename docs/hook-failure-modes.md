# Hook failure modes and how this hook handles them

A hook is only a control if it fails safely. These are the failure patterns that show up repeatedly in public agent-tool issue trackers (measured 2026-10-28, see the gap analysis) and what this example does about each.

| Failure mode | What goes wrong | What this hook does | Test |
|---|---|---|---|
| Hook crashes or its input is malformed | The action may proceed as if no hook existed | Every error exits 2 (block) | `test_bad_input_fails_closed` |
| Policy file missing or invalid | Silent allow | Exit 2 | `test_missing_policy_fails_closed` |
| Wrapped commands (`bash -c "..."`, `sudo`, `powershell -Command`) | The outer command looks harmless | The inner command is judged, up to four levels; `-lc`-style flags, `eval`, `xargs`, `find -exec`, `$(...)` bodies and here-documents are unwrapped | `Wrappers` in `test_hook_extra.py`, `tests/test_bypass_corpus.py` |
| Chained commands, including a single `&` (cmd) | Only the first command is checked | Highest tier of all parts wins; `2>&1` is not a separator | `Wrappers` |
| Windows commands and backslash paths | Unix-only rules miss `Remove-Item -Recurse -Force`, `rd /s`, `type .env` | Windows patterns in `policy/command-tiers.json`; paths normalised to `/`; PowerShell aliases and abbreviated parameters (`ri x -r -fo`) are recognised | `WindowsCommands`, `FileWrites`, corpus category `powershell` |
| File edits bypass a Bash-only hook | `Write`/`Edit` can change `.env` or CI files directly | `protected_paths` (ask) and `blocked_paths` (block) for Write/Edit/MultiEdit/NotebookEdit | `FileWrites` |
| Nothing records what was decided | No evidence after an incident | Tier 1, 2 and 3 decisions go to the hash-chained log when `AUDIT_LOG` is set | `AuditOfEveryDecision` |
| The agent edits its own rules | The gate is removed by the thing it gates | `policy/command-tiers.json`, `hooks/policy.json` and `CLAUDE.md` are protected paths (ask) | `FileWrites`, `test_new_policy_protects_itself` |
| Evasion: variables, quoting, absolute paths, newlines, decoded payloads | A regex per segment misses `X=rm; $X -rf y`, `"rm" -rf`, `/bin/rm -r -f`, a newline-chained command | Tokenizer, variable resolution, `rm`/`Remove-Item` flag parsing, unresolved names and uninspectable shells are tier 2 or higher | 185-case corpus, `python tools/replay_corpus.py` |
| Policy file invalid or incomplete | A typo silently weakens a rule | Strict schema: unknown schema, duplicate id, missing rationale, bad regex or missing check exits 2 | `StrictLoading` in `tests/test_policy_file.py` |

## Not covered (known limits)
- Obfuscated commands (encoded payloads, variables built at runtime, `read`, loops, aliases and functions defined in earlier calls) are not understood; they are tier 2 (ask) when the hook can see that it cannot tell, which is the fail-closed default, not a guarantee. The hook resolves only literal assignments in the same command line.
- The corpus in `tests/corpus/bypass_cases.jsonl` shows the evasion forms someone thought of. Passing it is not a proof of security.
- The hook cannot see what a script it allows does internally.
- It is not a sandbox. Use OS permissions, a non-admin account and branch protection as well.
- Hook configuration formats change between Claude Code versions; check the current documentation. Matcher to use for the extended hook: `Bash|PowerShell|Write|Edit|MultiEdit|NotebookEdit` (verify the tool names in your version).
