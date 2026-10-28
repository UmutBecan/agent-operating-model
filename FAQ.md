# FAQ and known limitations

## Frequently asked

**Does this work on Windows?** The scripts and hook are plain Python 3 (standard library only). The test suite was run on Windows 11 with Python 3.12 and passes (`python -m unittest discover -s tests`). On Linux and macOS it is expected to work but has not been run there by the author yet (unverified). Use `python` or `python3`, whichever your system has.

**How do I wire the hook into Claude Code?** See `docs/hook-setup.md`. Check the hook settings format against your Claude Code version; it changes.

**Is the hook a sandbox?** No. It is one layer that blocks, asks or allows by command tier and fails closed. Pair it with OS permissions.

**Which license?** Documents and templates: CC BY 4.0 (attribution required, see ATTRIBUTION.md). Software in `scripts/`, `hooks/`, `tests/`: MIT (see LICENSE-CODE). No third-party code is included; related projects are described, not copied, in `docs/prior-art.md`.

**Can I use this with agents other than Claude Code?** The templates are plain Markdown and work with any agent that reads an instruction file. The hook targets Claude Code's PreToolUse hook; other agents are untested.

**Do I need all the templates?** No. Start with `CLAUDE.md`, the decision register and the approval gates.

## Known limitations

- One-person system today; team use needs ownership and access rules not defined here.
- The hook matches command patterns; it cannot understand every shell construct, so obfuscated commands may need extra policy lines. Add a test for each bypass you find.
- Only English templates today. A Turkish translation is planned (see `docs/translation-plan.md`).
- No Linux or macOS test run recorded yet; CI draft in `.github/workflows/tests.yml` would produce one once published.
- Templates describe habits; they cannot make an agent follow them.
