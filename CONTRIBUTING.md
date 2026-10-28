# Contributing

Thanks for looking. This is a small, opinionated set of templates; changes that keep it small are the most welcome.

## Good contributions

- A **failure** you hit with AI agents that a rule here would have prevented (add to `docs/failure-log.md`, with what happened and the rule).
- A **CLAUDE.md variant** for another stack (see `templates/variants/`). Keep it short; the point is the gates, not the stack tutorial.
- **Tests** for `hooks/` and `scripts/`, especially edge cases where the hook could fail open.
- Corrections to `docs/prior-art.md`: a project we describe wrongly, or one that does it better.

## Ground rules

- Python 3 standard library only. No new dependencies.
- Run `python -m unittest discover -s tests` before opening a pull request. Do not lower the test count.
- Do not overwrite existing tests; extend them or add a clearly named companion file.
- Describe what something does, not how good it is. No unverifiable claims.
- Do not paste code or text from other projects unless the license allows it and you cite it.

## Process

Open an issue first for anything larger than a typo. Small pull requests, one change each. Be kind in review; this is a one-person project and replies may take a few days.

By contributing you agree that your documents are licensed under CC BY 4.0 and your code under MIT, as described in ATTRIBUTION.md.
