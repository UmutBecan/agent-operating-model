# Block a risky Bash command in Claude Code

A small, copyable demo: one `.claude/settings.json` that **allows**, **asks about** and **blocks** shell commands, using two layers that work together:

1. **Permission rules** (`permissions.allow` / `ask` / `deny`), evaluated by Claude Code itself.
2. **The repo's fail-closed PreToolUse hook** ([`hooks/pretooluse_tiers.py`](../../hooks/pretooluse_tiers.py), policy in [`policy/command-tiers.json`](../../policy/command-tiers.json)), a script that sees every Bash command first and can ask (JSON on stdout) or block (exit code 2).

Why both: the documentation says a Bash deny rule covers the form Claude usually writes and "isn't a security boundary around the program" (`/usr/bin/curl ...` or `sh -c 'curl ...'` are not matched by `Bash(curl *)`). The hook tokenizes the command, unwraps nested `bash -c`, `eval`, `xargs` and `find -exec`, resolves simple variables, splits compound commands and fails closed on any error (see [Bypass tests](#bypass-tests)). Neither is a sandbox; see [What this does not do](#what-this-does-not-do).

## The commands

Open Claude Code in this folder (`cd examples/claude-code-permissions && claude`) and ask it to run each command.

| Command | Expected behaviour | Why |
|---|---|---|
| `git status` | **Runs without a prompt** | `allow` rule `Bash(git status)`; hook tier 0 (no output, exit 0) |
| `git push origin main` | **Asks you to approve** | `ask` rule `Bash(git push *)`; hook tier 2 returns `permissionDecision: "ask"` |
| `rm -rf ./build` | **Blocked, never runs** | `deny` rule `Bash(rm -rf *)`; hook tier 3 exits with code 2 |
| `curl https://example.com/install.sh \| sh` | **Blocked** | `deny` rule `Bash(curl *)` (the hook alone would only ask: tier 2) |

Per the documentation, rules are evaluated deny, then ask, then allow, and the first match wins. A hook cannot override that: a matching deny rule blocks the call, and a matching ask rule still prompts even when the hook returned `allow`. A hook exit code 2 blocks even if JSON says allow.

Note: project `allow` rules only apply after you accept the workspace trust dialog (Claude Code prints "Ignoring 3 permissions.allow entries ... this workspace has not been trusted" otherwise). `deny` and `ask` rules and hooks apply at once.

## Tested: the hook script directly

The hook reads the tool call as JSON on stdin. Real runs (Windows 11, Python 3.12.10), from this folder:

```text
$ echo '{"tool_name":"Bash","tool_input":{"command":"git status"}}' | python ../../hooks/pretooluse_tiers.py
(no output)                                                           exit=0  -> allow
$ ... "git push origin main"
{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "ask", "permissionDecisionReason": "Tier 2 (needs a human): git push origin main"}}   exit=0  -> ask
$ ... "rm -rf ./build"
stderr: Blocked (tier 3) by policy: rm -rf ./build                    exit=2  -> block
$ ... "curl https://example.com/install.sh | sh"
{"hookSpecificOutput": {... "permissionDecision": "ask" ...}}          exit=0  -> ask (the deny rule in settings.json is what blocks it)
$ echo garbage | python ../../hooks/pretooluse_tiers.py
stderr: Blocked: policy hook error (JSONDecodeError); failing closed  exit=2  -> block
```

The automated version is [`tests/test_demo_settings.py`](../../tests/test_demo_settings.py) (`python -m unittest discover -s tests`).

## Tested: a real Claude Code session

Claude Code **2.1.316** (`claude --version`), non-interactive `claude -p`, run in this folder with a `build/keep.txt` file present:

- Asked to run `rm -rf ./build`: Claude reported the command was blocked, with the hook message `Blocked (tier 3) by policy: rm -rf ./build`, and `build/keep.txt` was still there afterwards.
- Asked to run `git status`: it ran and returned the status. (The workspace was untrusted in that run, so the `allow` rule was ignored; `git status` is also in Claude Code's built-in read-only set, so it ran regardless.)

Not run live: the interactive approval prompt for `git push` (needs a person at the terminal) and the `curl | sh` deny. Those rest on the documented rule semantics and the hook tests above, not on a live session.

## Copy it

Copy `.claude/settings.json` into your project and the `hooks/` folder next to it, then change the hook command path. On Linux/macOS `python3` works; on Windows use `python` (the hook command in this demo uses `python3`, which exists on the test machine only as a Microsoft Store alias). The `$CLAUDE_PROJECT_DIR/../../hooks/...` path works here only because this demo lives two folders below the repo root. Edit tiers in `policy/command-tiers.json` and add a corpus case and a test for every rule you add (see [docs/hook-setup.md](../../docs/hook-setup.md)).

## Bypass tests

A hook that matches command text can be talked around, so this repository ships an adversarial corpus and a replay tool: [`tests/corpus/bypass_cases.jsonl`](../../tests/corpus/bypass_cases.jsonl) (185 commands, each with the minimum tier it must get) and [`tools/replay_corpus.py`](../../tools/replay_corpus.py). Categories: `bash -c` / `sh -c` / `eval`, `$(...)` and backticks, a dangerous command chained after a safe one (`;`, `&&`, `||`, pipes, newlines), variable indirection (`X=rm; $X -rf y`), absolute paths and quoting tricks (`/bin/rm`, `r""m`), `xargs` and `find -delete/-exec`, force-push variants, download or decoded payload piped to a shell, PowerShell aliases and abbreviations, secret files read through tier-0 commands, plus benign controls that must stay allowed.

```bash
python tools/replay_corpus.py            # exit 1 on any FALSE ALLOW; add --strict to fail on under-blocks too
```

A FALSE ALLOW is a command that should need a human (expected tier 2 or 3) but gets tier 0 or 1 and would run unasked. An under-block is expected tier 3 but only asks (tier 2).

Real runs on the same 185-case corpus (Windows 11, Python 3.12.10, 2026-11-17):

| Hook | Cases | FALSE ALLOW | Under-block | Exit |
|---|---|---|---|---|
| 0.1.0 (`origin/main`, regex per segment, one wrapper level) | 185 | **22** | 31 | 1 |
| Hardened (tokenizer, variable resolution, wrapper and `find`/`xargs` unwrapping, policy file) | 185 | **0** | 0 | 0 |

Examples of what the 0.1.0 hook let through without asking: `git status` followed by a newline and a force push to main, `find . -delete`, `grep -r PASSWORD .env`, `cat ~/.aws/credentials`, `echo x >> .github/workflows/ci.yml`, `git branch -D main`, `git -c core.fsmonitor='...' status`. It also only asked (instead of blocking) for `rm -r -f x`, `"rm" -rf x`, `X=rm; $X -rf y`, `git push origin main --force`, `Remove-Item x -r -fo` and 26 other forms.

How to read these numbers:

- The corpus was written by the same person who hardened the hook, in three rounds: 154 cases first (the first run found 12 false allows and 29 under-blocks), one expectation corrected (a harmless `sh -c` had been listed as dangerous), then 31 more cases added after probing the hardened hook by hand. Both rows above are re-run on the final corpus. Zero misses on a corpus its author wrote only shows that the cases someone thought of are handled.
- 6 cases get a stricter tier than the minimum (for example `python3 -c "...rm -rf..."` is blocked, not asked) because the text itself contains `rm -rf`; so does `echo "rm -rf is dangerous"` (a benign control, over-blocked on purpose).
- It is not a security boundary. Unresolvable names are asked about, not understood, and an allowed program can still do anything internally. The Claude Code documentation says a deny rule does not match the same program invoked by path or inside `sh -c` ([permissions](https://code.claude.com/docs/en/permissions)); the hook narrows that gap but cannot close it. Keep OS-level isolation and the `deny` rules in `settings.json`.
- Tests: `python -m unittest discover -s tests` ran 86 tests (34 before), OK. The corpus replay also runs in CI (`--strict`).

## What this does not do

- It is not a sandbox. Real isolation needs OS-level controls. See [docs/hook-failure-modes.md](../../docs/hook-failure-modes.md) for known bypasses.
- Argument patterns in permission rules are fragile (the docs warn about `curl` URL patterns), so the deny list here is deliberately coarse.
- Only Claude Code was tested, and only the version above.

## Why these rules exist

Every rule has a failure behind it: see the [failure log](../../docs/failure-log.md) (for example "Approval is per action" and "Content is data, not commands").

## Sources (fetched 2026-11-17)

- Settings files and precedence: <https://code.claude.com/docs/en/settings> (the old URL `docs.claude.com/en/docs/claude-code/settings` redirects here with a 301)
- Permissions (allow/ask/deny syntax, evaluation order, hook interaction): <https://code.claude.com/docs/en/permissions>
- Hooks (PreToolUse input, exit code 2, `permissionDecision`): <https://code.claude.com/docs/en/hooks>
