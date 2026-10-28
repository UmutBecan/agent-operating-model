# Security policy

This repository contains templates, a small PreToolUse hook and helper scripts. It is an **example, not a sandbox**: do not rely on it as your only control.

## Reporting a problem

If you find a way the hook (`hooks/pretooluse_tiers.py`) lets a command through that the policy says to block or ask for, or any other security issue, please open a **private security advisory** on GitHub (Security tab, "Report a vulnerability"). If that is not available, open an issue that describes the bypass class without a working exploit.

Expect a first reply within about a week (best effort, one maintainer).

## Scope

In scope: the hook and its policy file, `scripts/`. Out of scope: your agent platform, your OS permissions, and any claim that the templates make an agent safe on their own.
