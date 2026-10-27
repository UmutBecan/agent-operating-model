# Variant: web product

Append to `CLAUDE.md`, then fill in the commands.

## Commands
- Build: `<build command>` · Test: `<test command>` · Lint and types: `<check command>`

## Release gate
A release candidate needs: build, full automated tests, browser checks on desktop and mobile, a dependency and secret scan, and a review of what changed. Report the status as it is, including what was not tested. **Only the owner passes the visual and release gates.**

## Product rules
- Every visible control is active, partial or coming soon. No dead buttons, no fake-working feature.
- Security-relevant checks and scores are rules, not model guesses.
- If a feature stores data, update the privacy notice in the same change.
- Never overwrite an existing test; extend it or add a companion file. Test counts do not drop without a written reason.
