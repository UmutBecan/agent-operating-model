# Hook setup (Windows and Linux/macOS)

Verify the settings format against the Claude Code documentation for your version before relying on this. It is an example, not a guarantee.

1. Copy `hooks/pretooluse_tiers.py` and `policy/command-tiers.json` into your project, for example `.claude/hooks/` (the hook also finds `command-tiers.json` next to itself). `hooks/policy.json` is the 0.1.0 format; it still loads but is deprecated.
2. Register a PreToolUse hook (matcher `Bash|PowerShell|Write|Edit|MultiEdit|NotebookEdit`; verify tool names in your version) in your Claude Code settings, with this command:
   - Linux/macOS: `python3 .claude/hooks/pretooluse_tiers.py`
   - Windows (PowerShell or cmd): `python .claude\hooks\pretooluse_tiers.py`
3. Test it without the agent: pipe a sample tool-call JSON to the script and check the exit code. Exit code 2 means block. The tests in `tests/test_hook.py` show the input shape.
4. Edit `command-tiers.json` to match your commands (format and review rules: [policy/README.md](../policy/README.md)). Add a case to `tests/corpus/bypass_cases.jsonl` and a test for every rule you add, then run `python tools/replay_corpus.py --strict`.

Fail-closed: any error inside the hook is treated as a block, because a crashed hook can otherwise let an action through.
