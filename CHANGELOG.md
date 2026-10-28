# Changelog

Format follows Keep a Changelog; versions follow Semantic Versioning. Dates are Europe/Istanbul.

## [Unreleased]

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
