# Hook setup (Windows and Linux/macOS)

Verify the settings format against the Claude Code documentation for your version before relying on this. It is an example, not a guarantee.

1. Copy `hooks/pretooluse_tiers.py` and `hooks/policy.json` into your project, for example `.claude/hooks/`.
2. Register a PreToolUse hook (matcher `Bash|PowerShell|Write|Edit|MultiEdit|NotebookEdit`; verify tool names in your version) in your Claude Code settings, with this command:
   - Linux/macOS: `python3 .claude/hooks/pretooluse_tiers.py`
   - Windows (PowerShell or cmd): `python .claude\hooks\pretooluse_tiers.py`
3. Test it without the agent: pipe a sample tool-call JSON to the script and check the exit code. Exit code 2 means block. The tests in `tests/test_hook.py` show the input shape.
4. Edit `policy.json` tiers to match your commands. Add a test for every rule you add.

Fail-closed: any error inside the hook is treated as a block, because a crashed hook can otherwise let an action through.
