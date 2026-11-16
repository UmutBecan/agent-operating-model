# Command tier policy

`command-tiers.json` is the reviewable policy behind [`hooks/pretooluse_tiers.py`](../hooks/pretooluse_tiers.py). The hook holds the mechanism (how a command line is split and unwrapped); this file holds every decision, each with an id and a rationale, so a change is a diff a person can review.

This is defense in depth on top of Claude Code's own permission rules. It is not a security boundary: the Claude Code documentation says a Bash deny rule does not match the same program invoked by path or inside `sh -c` ([permissions](https://code.claude.com/docs/en/permissions), read 2026-11-17), and a hook that reads command text has the same kind of limits (see [What it cannot do](#what-it-cannot-do)). Use OS-level isolation as well.

## Format (`schema: "command-tiers/1"`)

| Section | Content |
|---|---|
| `version` | Semantic version of the policy. Patch: wording only. Minor: rules added or made stricter. Major: a decision gets looser, or the schema changes. The version is written to every audit entry. |
| `rules[]` | `id` (`T<tier>-<name>`), `tier` 0-3, `pattern` (regular expression, case-insensitive), `rationale`. Matched against each normalized command segment; the most restrictive tier wins; no match means `default_tier` (2, ask). Tier-3 patterns are also matched against the raw text. |
| `path_rules[]` | `id`, `kind` (`protected` = ask, `blocked` = block), `pattern`, `rationale`. Applied to Write/Edit targets and to shell redirect targets. |
| `checks[]` | Tier and rationale for each check the hook code performs (recursive delete flags, force push to a protected branch, shells it cannot inspect, `eval`, `find -delete`, unresolved command names, ...). The set of ids is fixed by the hook; a policy that omits one is rejected. |
| `structure` | Data the checks need: shell names, wrapper commands such as `sudo` and `nohup` (with their options), protected branches, git global options. |

## Loading rules

- `POLICY_FILE` set: that file only. Otherwise `policy/command-tiers.json` next to `hooks/`, then `command-tiers.json` next to the hook script (for a copied `.claude/hooks/` folder), then the legacy `hooks/policy.json`.
- A file that exists but is invalid (bad JSON, unknown schema, duplicate id, missing rationale, invalid regular expression, missing check, tier outside 0-3) makes the hook exit 2. There is no fallback to a weaker policy. A missing file also exits 2.
- `hooks/policy.json` is the 0.1.0 format. It still loads (the hook accepts both) and the original tests still run against it, but new rules belong in `command-tiers.json`. `tests/test_policy_file.py` checks that every legacy rule is carried over except four documented changes.

## Adding or changing a rule

1. Add the rule with a new id and a rationale that says what harm it prevents.
2. Add the commands it should catch (and a benign neighbour it must not catch) to [`tests/corpus/bypass_cases.jsonl`](../tests/corpus/bypass_cases.jsonl).
3. Run `python tools/replay_corpus.py --strict` and `python -m unittest discover -s tests`.
4. Bump `version` as described above.

## What it cannot do

- Variables it cannot resolve, command names produced by `$(...)`, and scripts a shell runs from a file are asked about (tier 2), not understood.
- It reads command text. It cannot see what an allowed program does internally (`make`, `npm run build`, a script in the repository).
- Aliases, shell functions defined in earlier calls, and files sourced from the environment are outside what one command line shows.
- Variable resolution is linear and literal: it does not follow branches, loops, `read`, or arithmetic.
