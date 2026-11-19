# Changelog

Format follows Keep a Changelog; versions follow Semantic Versioning. Dates are Europe/Istanbul.

## [Unreleased]
### Added
- `policy/command-tiers.json`: the tier rules as a versioned, reviewable policy (rule ids, rationale, strict loading, fail-closed on a missing or invalid file); `policy/README.md`. `hooks/policy.json` (0.1.0 format) still loads.
- `tests/corpus/bypass_cases.jsonl` (185 evasion cases) and `tools/replay_corpus.py` (confusion summary, exit 1 on a false allow); CI runs it with `--strict`. On the same corpus the 0.1.0 hook had 22 false allows and 31 under-blocks; the hardened hook has 0 and 0. Not a security boundary.
- Tests: `tests/test_policy_file.py`, `tests/test_bypass_corpus.py` (86 tests in total, was 34).
### Fixed
- `scripts/audit_chain.py`: `append` now holds an exclusive lock (fcntl, msvcrt on Windows) while it reads the last hash and writes the entry, so parallel hook processes no longer fork the chain (issue #1). A damaged tail is refused with a clear error instead of being chained onto; `verify` reports it as BROKEN instead of crashing. Tests: `tests/test_audit_chain_concurrency.py` (6 parallel writers, 120 entries; 3 runs OK on Linux).
### Changed
- Hook: shell-aware tokenizer, nested wrapper unwrapping, simple variable resolution, `rm`/`Remove-Item` flag parsing, `find`/`xargs`/`eval`/`source` handling, git global options, redirect targets checked against protected and blocked paths, secret files caught for any command. Audit entries record the policy version.
- Policy: `dd if=` is now matched (the 0.1.0 pattern could not match it); `npx` no longer tier 0 (`npx test` runs a downloaded package); `git branch -D`, `rg --pre`, `git diff --output`, `date -s` and similar tier-0 commands with side effects now ask.

## [0.1.0] - 2026-10-28
First tagged release: templates, scripts, a fail-closed PreToolUse hook, documents under CC BY 4.0 and software under MIT, 28 tests (Windows and Linux CI).
### Changed
- Documents are now licensed under CC BY 4.0 (attribution required); software stays MIT in `LICENSE-CODE`. Added ATTRIBUTION.md. Earlier copies remain under MIT for those who received them.
### Added
- Hook: shell-wrapper unwrapping, single-ampersand chains, Windows/PowerShell tiers, protected and blocked paths for Write/Edit, audit of tier 1-3 decisions; tests in tests/test_hook_extra.py (28 tests total).
- docs/hook-failure-modes.md, docs/skill-and-mcp-intake-checklist.md.
- CONTRIBUTING, SECURITY, FAQ and known limitations, CITATION.cff, issue and pull request templates.
- Hook setup guide for Windows and Linux/macOS, translation plan, CI workflow draft.
- Social preview image source (docs/assets/social-preview.png).

## 2026-10-27
### Added
- Instruction linter and CLAUDE.md variants (web product, infrastructure, research).
- PreToolUse hook enforcing command tiers (fail-closed), with tests.

## 2026-10-26
### Added
- Initial templates, scripts and docs.
