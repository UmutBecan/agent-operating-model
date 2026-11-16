#!/usr/bin/env python3
"""Claude Code PreToolUse hook: classify a Bash command into tiers 0-3 (see templates/command-tiers.md).

    tier 0  free      -> allow
    tier 1  logged    -> allow, and append to the audit chain if AUDIT_LOG is set
    tier 2  ask       -> ask the human (permissionDecision "ask")
    tier 3  blocked   -> deny with exit code 2 and a reason on stderr

Fail closed: an unknown command is tier 2, and any error while reading the input or the
policy is tier 3. A hook that crashes can let the action proceed, so everything below is
wrapped and exits 2 on error.

Wire it in .claude/settings.json (check the hook format against your Claude Code version):
  {"hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command",
     "command": "python3 /path/to/hooks/pretooluse_tiers.py"}]}]}}

Policy: policy/command-tiers.json (versioned rules with ids and rationale; see policy/README.md).
Lookup order: POLICY_FILE if set (that file only), else policy/command-tiers.json next to hooks/,
else command-tiers.json next to this script, else the legacy hooks/policy.json. A file that exists
but is invalid is an error (exit 2); there is no fallback to a weaker policy.

How a command is judged (defense in depth, not a security boundary):
  1. the text is tokenized like a shell (quotes, escapes, operators, newlines) and split into segments;
  2. simple variable assignments are resolved, wrappers (sudo, env, nohup, ...) and absolute paths are
     stripped, `bash -c`, `eval`, `xargs`, `find -exec` and `$(...)` bodies are judged by what they run;
  3. what cannot be inspected (unknown variable as a command name, encoded commands, scripts run by
     a shell) is at least tier 2;
  4. every segment is matched against the policy rules, most restrictive tier wins.
This is an example, not a sandbox: real isolation needs OS-level controls as well.
"""
import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SHELL_TOOLS = ("Bash", "PowerShell")
WRITE_TOOLS = ("Write", "Edit", "MultiEdit", "NotebookEdit")
SCHEMA = "command-tiers/1"
MAX_DEPTH = 4
KEYWORDS = ("{", "}", "!", "if", "then", "else", "elif", "fi", "do", "done", "while", "until")  # shell grammar, no command
CHECK_IDS = ("C-recursive-delete", "C-force-push-protected", "C-shell-uninspectable", "C-eval", "C-source",
             "C-opaque-command-name", "C-find-delete", "C-substitution", "C-unparseable", "C-depth-exceeded", "C-git-config-override")
LEGACY_STRUCTURE = {  # what the 0.1.0 hook assumed; used only for the legacy policy format
    "shells": {"posix": ["bash", "sh", "zsh"], "powershell": ["pwsh", "powershell"], "cmd": ["cmd"]},
    "prefix_commands": {"sudo": {}, "env": {}},
    "eval_commands": [], "source_commands": [], "recursive_delete_commands": [],
    "git": {"value_global_opts": [], "protected_branches": []}, "xargs_value_opts": [],
}
LEGACY_CHECKS = {"C-shell-uninspectable": 2, "C-substitution": 2, "C-unparseable": 2, "C-depth-exceeded": 2}


# ---------------------------------------------------------------- policy loading

def _compile(pattern, where):
    try:
        return re.compile(pattern, re.I)
    except re.error as e:
        raise ValueError(f"{where}: invalid pattern {pattern!r}: {e}") from e


def _tier(value, where):
    if isinstance(value, bool) or value not in (0, 1, 2, 3):
        raise ValueError(f"{where}: tier must be 0, 1, 2 or 3")
    return value


def _build_legacy(pol, raw):
    rules = {t: [(f"legacy-t{t}-{i + 1}", _compile(p, f"tier{t}")) for i, p in enumerate(pol.get(f"tier{t}", []))] for t in range(4)}
    paths = {k: [(f"legacy-{k}-{i + 1}", _compile(p, k)) for i, p in enumerate(pol.get(k, []))] for k in ("protected_paths", "blocked_paths")}
    return {"format": "legacy", "version": "legacy", "sha256": hashlib.sha256(raw).hexdigest(), "rules": rules,
            "protected_paths": paths["protected_paths"], "blocked_paths": paths["blocked_paths"],
            "structure": LEGACY_STRUCTURE, "checks": dict(LEGACY_CHECKS), "default_tier": 2}


def _build(pol, raw):
    if pol.get("schema") != SCHEMA:
        raise ValueError(f"unsupported policy schema {pol.get('schema')!r} (expected {SCHEMA!r})")
    version = pol.get("version")
    if not isinstance(version, str) or not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError("policy version must be a string like 1.0.0")
    default_tier = _tier(pol.get("default_tier", 2), "default_tier")
    seen, rules = set(), {t: [] for t in range(4)}
    for r in pol.get("rules", []):
        rid = r.get("id")
        if not isinstance(rid, str) or not rid or rid in seen:
            raise ValueError(f"rule id missing or duplicated: {rid!r}")
        seen.add(rid)
        if not r.get("rationale"):
            raise ValueError(f"rule {rid}: rationale is required")
        rules[_tier(r.get("tier"), rid)].append((rid, _compile(r.get("pattern", ""), rid)))
    paths = {"protected": [], "blocked": []}
    for r in pol.get("path_rules", []):
        rid = r.get("id")
        if not isinstance(rid, str) or not rid or rid in seen:
            raise ValueError(f"path rule id missing or duplicated: {rid!r}")
        seen.add(rid)
        if r.get("kind") not in paths or not r.get("rationale"):
            raise ValueError(f"path rule {rid}: kind must be protected or blocked, and a rationale is required")
        paths[r["kind"]].append((rid, _compile(r.get("pattern", ""), rid)))
    checks = {}
    for c in pol.get("checks", []):
        if c.get("id") not in CHECK_IDS or not c.get("rationale"):
            raise ValueError(f"unknown check or missing rationale: {c.get('id')!r}")
        checks[c["id"]] = _tier(c.get("tier"), c["id"])
    missing = [i for i in CHECK_IDS if i not in checks]
    if missing:
        raise ValueError(f"policy lacks required checks: {', '.join(missing)}")
    structure = pol.get("structure")
    if not isinstance(structure, dict):
        raise ValueError("policy lacks a structure section")
    for key in LEGACY_STRUCTURE:
        if key not in structure:
            raise ValueError(f"structure lacks {key!r}")
    return {"format": SCHEMA, "version": version, "sha256": hashlib.sha256(raw).hexdigest(), "rules": rules,
            "protected_paths": paths["protected"], "blocked_paths": paths["blocked"], "structure": structure,
            "checks": checks, "default_tier": default_tier}


def _policy_path(path):
    if path:
        return path
    if os.environ.get("POLICY_FILE"):
        return os.environ["POLICY_FILE"]
    for cand in (os.path.join(HERE, "..", "policy", "command-tiers.json"), os.path.join(HERE, "command-tiers.json"),
                 os.path.join(HERE, "policy.json")):
        if os.path.exists(cand):
            return cand
    return os.path.join(HERE, "..", "policy", "command-tiers.json")  # does not exist: open() fails, hook exits 2


def load_policy(path=None):
    """Load and validate a policy; raises on a missing or invalid file (the hook then exits 2)."""
    with open(_policy_path(path), "rb") as f:
        raw = f.read()
    pol = json.loads(raw.decode("utf-8"))
    if not isinstance(pol, dict):
        raise ValueError("policy must be a JSON object")
    return _build_legacy(pol, raw) if "tier3" in pol and "schema" not in pol else _build(pol, raw)


def path_tier(path, pol):
    """Tier for a file write: 3 = blocked path, 2 = protected path (ask), 0 = open."""
    return path_tier_detail(path, pol)[0]


def path_tier_detail(path, pol):
    norm = str(path).replace("\\", "/")
    for rid, p in pol["blocked_paths"]:
        if p.search(norm):
            return 3, rid
    for rid, p in pol["protected_paths"]:
        if p.search(norm):
            return 2, rid
    return 0, None


# ---------------------------------------------------------------- lexing

OPS = re.compile(r">>|>&|&>>|&>|>\||<<<|<<|<&|<|\|\||&&|\|&|\||;;|;|&|\(|\)")
REDIRECTS = {">", ">>", ">&", "&>", "&>>", ">|", "<", "<<", "<<<", "<&"}
WRITE_REDIRECTS = {">", ">>", "&>", "&>>", ">|"}
SEPARATORS = {"|", "||", "&&", "&", ";", ";;", "|&", "(", ")"}


class Unparseable(ValueError):
    pass


def lex(s, windows=False):
    """Split shell text into (text, is_operator) tokens. Quotes and escapes are resolved; unquoted
    newlines become `;`; an unbalanced quote raises Unparseable. windows=True: backslash is literal."""
    toks, buf, have, i, n = [], [], False, 0, len(s)

    def flush():
        nonlocal buf, have
        if have:
            toks.append(("".join(buf), False))
        buf, have = [], False

    while i < n:
        c = s[i]
        if c in " \t\r":
            flush()
            i += 1
        elif c == "\n":
            flush()
            toks.append((";", True))
            i += 1
        elif c == "\\" and not windows:
            if i + 1 < n and s[i + 1] == "\n":
                i += 2
            elif i + 1 < n:
                buf.append(s[i + 1])
                have = True
                i += 2
            else:
                i += 1
        elif c == "`" and windows:
            if i + 1 < n:
                buf.append(s[i + 1])
                have = True
            i += 2
        elif c == "`":
            flush()
            toks.append((";", True))
            i += 1
        elif c == "'":
            j = s.find("'", i + 1)
            if j < 0:
                raise Unparseable("unbalanced single quote")
            buf.append(s[i + 1:j])
            have = True
            i = j + 1
        elif c == '"':
            i += 1
            while True:
                if i >= n:
                    raise Unparseable("unbalanced double quote")
                d = s[i]
                if d == '"':
                    if windows and i + 1 < n and s[i + 1] == '"':
                        buf.append('"')
                        i += 2
                        continue
                    i += 1
                    break
                if d == "\\" and not windows and i + 1 < n and s[i + 1] in '"\\$`\n':
                    if s[i + 1] != "\n":
                        buf.append(s[i + 1])
                    i += 2
                elif d == "`" and windows and i + 1 < n:
                    buf.append(s[i + 1])
                    i += 2
                else:
                    buf.append(d)
                    i += 1
            have = True
        elif c in ";&|()<>":
            flush()
            j = i
            while j < n and s[j] in ";&|()<>":
                j += 1
            for m in OPS.finditer(s[i:j]):
                toks.append((m.group(0), True))
            i = j
        else:
            buf.append(c)
            have = True
            i += 1
    flush()
    return toks


def split_segments(toks):
    segs, cur = [], []
    for text, is_op in toks:
        if is_op and text in SEPARATORS:
            segs.append(cur)
            cur = []
        else:
            cur.append((text, is_op))
    segs.append(cur)
    return [s for s in segs if s]


def sub_bodies(s):
    """Bodies of $(...), <(...), >(...) (balanced) and of `...`; quotes are ignored on purpose (over-inspect)."""
    out = []
    for m in re.finditer(r"[$<>]\(", s):
        depth, j = 1, m.end()
        while j < len(s) and depth:
            depth += (s[j] == "(") - (s[j] == ")")
            j += 1
        out.append(s[m.end():j - 1 if depth == 0 else j])
    parts = s.split("`")
    out.extend(parts[1::2])
    return out


# ---------------------------------------------------------------- classification

ASSIGN = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$", re.S)
VAR = re.compile(r"\$(?:\{([A-Za-z_][A-Za-z0-9_]*)\}|([A-Za-z_][A-Za-z0-9_]*))")


class Ctx:
    def __init__(self, pol):
        self.pol, self.hits = pol, []

    def bump(self, tier, rid):
        self.hits.append((tier, rid))
        return tier


def expand(word, env):
    """Replace known simple variables; $IFS becomes a space. Unknown variables stay as text. Returns (text, changed)."""
    def rep(m):
        name = m.group(1) or m.group(2)
        if name == "IFS":
            return " "
        return env.get(name, m.group(0))

    out = VAR.sub(rep, word)
    return out, out != word


def basename(word):
    b = re.split(r"[\\/]", word)[-1].lower()
    return b[:-4] if b.endswith(".exe") else b


def _tokens_to_words(seg):
    """Separate redirects from words. Returns (words, redirects)."""
    words, redirects, i = [], [], 0
    while i < len(seg):
        text, is_op = seg[i]
        if is_op and text in REDIRECTS:
            target = seg[i + 1][0] if i + 1 < len(seg) and not seg[i + 1][1] else None
            if words and re.fullmatch(r"\d+", words[-1]):
                words.pop()  # file descriptor number as in 2>/dev/null
            if text in ("<<", "<<<", ">&", "<&"):
                pass  # here-document/string data, or fd duplication such as 2>&1: not a path
            elif target is not None:
                redirects.append((text, target))
            i += 2 if target is not None else 1
            continue
        if is_op:
            i += 1
            continue
        words.append(text)
        i += 1
    return words, redirects


PS_VALUE_OPTS = {"-ep", "-executionpolicy", "-w", "-windowstyle", "-wd", "-workingdirectory", "-inputformat",
                 "-outputformat", "-version", "-configurationname"}


def powershell_inner(args):
    """Return (kind, text): kind is 'inline' (text is the command), 'opaque' (encoded command or script file)."""
    j = 0
    while j < len(args):
        low = args[j].lower()
        if low.startswith("-") and len(low) > 1:
            name = low[1:]
            if name in ("e", "ec") or (name[0] == "e" and "encodedcommand".startswith(name)):
                return "opaque", ""
            if name[0] == "f" and "file".startswith(name):
                return "opaque", ""
            if name[0] == "c" and "command".startswith(name):
                return "inline", " ".join(args[j + 1:])
            j += 2 if low in PS_VALUE_OPTS else 1
        else:
            return "inline", " ".join(args[j:])  # positional text is run as a command
    return "opaque", ""


def classify_words(words, env, ctx, depth, windows, redirects=()):
    """Judge one simple command given as a list of unquoted words. Returns a tier."""
    pol, st = ctx.pol, ctx.pol["structure"]
    best = 0
    for op, target in redirects:  # a redirect can overwrite a protected file even after a tier-0 command
        if op in WRITE_REDIRECTS:
            t, rid = path_tier_detail(target, pol)
            if t:
                best = max(best, ctx.bump(t, rid))
    # expand simple known variables (with word splitting of what was substituted); $IFS is a space
    expanded = []
    for w in words:
        text, changed = expand(w, env)
        expanded.extend((text.split() or [""]) if changed else [text])
    words = expanded
    # leading VAR=value words: alone they persist for later segments, before a command they are local
    assigns = []
    while words and ASSIGN.match(words[0]):
        assigns.append(ASSIGN.match(words[0]))
        words = words[1:]
    if not words:
        for m in assigns:
            env[m.group(1)] = m.group(2)
        return best
    if words[0] in ("export", "declare", "typeset", "readonly", "local") and len(words) > 1:
        for w in words[1:]:
            m = ASSIGN.match(w)
            if m:
                env[m.group(1)] = m.group(2)
        if all(ASSIGN.match(w) or w.startswith("-") for w in words[1:]):
            return best
    # prefix commands (sudo, env, nohup, time, exec, ...): their options are skipped
    while words:
        spec = st["prefix_commands"].get(basename(words[0]))
        if spec is None:
            break
        name = basename(words[0])
        value_opts = spec.get("value_opts", [])
        j = 1
        while j < len(words):
            w = words[j]
            if name == "env" and ASSIGN.match(w):
                m = ASSIGN.match(w)
                env[m.group(1)] = m.group(2)
                j += 1
            elif w in value_opts:
                j += 2
            elif w.startswith("-") and w != "-":
                j += 1
            else:
                break
        words = words[j + spec.get("positional", 0):]
        if not words and name not in KEYWORDS:  # `sudo -i`: a prefix with no command is an interactive shell or a no-op
            return max(best, ctx.bump(pol["default_tier"], "default-unknown"))
    if not words:
        return best
    cmd, args = basename(words[0]), words[1:]
    canon_words = [cmd] + args
    if re.search(r"\$|^\{.*,.*\}$", words[0]):  # unknown variable, ANSI-C quote or brace expansion as a command name
        best = max(best, ctx.bump(pol["checks"].get("C-opaque-command-name", 2), "C-opaque-command-name"))
    shells = st["shells"]
    if cmd in shells["posix"] or cmd in shells["powershell"] or cmd in shells["cmd"]:
        inner, inner_windows = None, False
        if cmd in shells["posix"]:
            for k, a in enumerate(args):
                if re.fullmatch(r"-[a-zA-Z]*c[a-zA-Z]*", a) and k + 1 < len(args):
                    inner = args[k + 1]
                    break
        elif cmd in shells["powershell"]:
            kind, text = powershell_inner(args)
            inner, inner_windows = (text if kind == "inline" else None), True
        else:
            for k, a in enumerate(args):
                if a.lower() in ("/c", "/k", "/r"):
                    inner, inner_windows = " ".join(args[k + 1:]), True
                    break
        if inner is not None and inner.strip():
            return max(best, classify_text(inner, ctx, depth - 1, inner_windows, dict(env)))
        best = max(best, ctx.bump(pol["checks"]["C-shell-uninspectable"], "C-shell-uninspectable"))
    elif cmd in st["eval_commands"]:
        best = max(best, ctx.bump(pol["checks"].get("C-eval", 2), "C-eval"))
        if args:
            best = max(best, classify_text(" ".join(args), ctx, depth - 1, windows, dict(env)))
    elif cmd in st["source_commands"]:
        best = max(best, ctx.bump(pol["checks"].get("C-source", 2), "C-source"))
    elif cmd == "xargs":
        j = 0
        while j < len(args) and args[j].startswith("-"):
            j += 2 if args[j] in st["xargs_value_opts"] else 1
        if j < len(args):  # xargs itself is neutral: it is judged by the command it runs
            return max(best, classify_words(args[j:], dict(env), ctx, depth - 1, windows))
    elif cmd == "find":
        for k, a in enumerate(args):
            if a == "-delete":
                best = max(best, ctx.bump(pol["checks"].get("C-find-delete", 2), "C-find-delete"))
            if a in ("-exec", "-execdir", "-ok", "-okdir"):
                j = k + 1
                while j < len(args) and args[j] not in (";", "+"):
                    j += 1
                if args[k + 1:j]:
                    best = max(best, classify_words(args[k + 1:j], dict(env), ctx, depth - 1, windows))
    elif cmd == "git":
        gl = st["git"]
        j = 0
        while j < len(args) and args[j].startswith("-"):
            if args[j] in ("-c", "--config-env") or args[j].startswith("--config-env="):
                best = max(best, ctx.bump(pol["checks"].get("C-git-config-override", 2), "C-git-config-override"))
            j += 2 if (args[j] in gl["value_global_opts"]) else 1
        canon_words = ["git"] + args[j:]
        if args[j:j + 1] == ["push"] and "C-force-push-protected" in pol["checks"]:
            rest = args[j + 1:]
            force = any(a in ("-f", "--force", "--mirror") or a.startswith(("--force-with-lease", "--force-if-includes"))
                        or re.fullmatch(r"-[a-zA-Z]*f[a-zA-Z]*", a) is not None or a.startswith("+") for a in rest)
            branches = {re.sub(r"^refs/heads/", "", a.lstrip("+").split(":")[-1]) for a in rest if not a.startswith("-")}
            if force and branches & set(gl["protected_branches"]):
                best = max(best, ctx.bump(pol["checks"]["C-force-push-protected"], "C-force-push-protected"))
    if cmd in st["recursive_delete_commands"] and "C-recursive-delete" in pol["checks"]:
        recursive = force = False
        for a in args:
            if a == "--":
                break
            if a == "--recursive":
                recursive = True
            elif a == "--force":
                force = True
            elif a.startswith("-") and not a.startswith("--") and len(a) > 1:
                name = a[1:]
                if re.fullmatch(r"[rRfidvIxPW]+", name):  # POSIX-style bundle such as -rf
                    recursive |= bool(re.search(r"[rR]", name))
                    force |= "f" in name
                else:  # PowerShell parameter, possibly abbreviated (-Recurse, -Rec, -Force, -fo)
                    low = name.lower()
                    recursive |= bool(re.fullmatch(r"r(e(c(u(r(se?)?)?)?)?)?", low))
                    force |= bool(re.fullmatch(r"fo(r(c(e)?)?)?", low))
        if recursive and force:
            best = max(best, ctx.bump(pol["checks"]["C-recursive-delete"], "C-recursive-delete"))
    return max(best, rule_tier(" ".join(canon_words + [t for _, t in redirects]), ctx))


def rule_tier(text, ctx):
    pol = ctx.pol
    for tier in (3, 2, 1, 0):  # most restrictive first
        for rid, p in pol["rules"][tier]:
            if p.search(text):
                ctx.bump(tier, rid)
                return tier
    return ctx.bump(pol["default_tier"], "default-unknown")


def classify_text(command, ctx, depth, windows, env):
    pol = ctx.pol
    command = str(command)
    best = 0
    if depth <= 0:
        return ctx.bump(max(pol["checks"]["C-depth-exceeded"], 3 if rule_hits_tier3(command, ctx) else 0), "C-depth-exceeded")
    if "$(" in command or "`" in command or "<(" in command or ">(" in command:
        best = ctx.bump(pol["checks"]["C-substitution"], "C-substitution")
    for body in sub_bodies(command):
        best = max(best, classify_text(body, ctx, depth - 1, windows, dict(env)))
    if rule_hits_tier3(command, ctx):  # unanchored tier-3 rules also see the raw text
        best = 3
    try:
        segments = split_segments(lex(command, windows))
    except Unparseable:
        return max(best, ctx.bump(pol["checks"]["C-unparseable"], "C-unparseable"))
    for seg in segments:
        words, redirects = _tokens_to_words(seg)
        if words or redirects:
            best = max(best, classify_words(words, env, ctx, depth, windows, redirects))
    return best


def rule_hits_tier3(text, ctx):
    for rid, p in ctx.pol["rules"][3]:
        if p.search(text):
            ctx.bump(3, rid)
            return True
    return False


def classify_detail(command, pol, windows=False):
    """Return (tier, [(tier, rule_or_check_id), ...]) for a command line."""
    ctx = Ctx(pol)
    tier = classify_text(command, ctx, MAX_DEPTH, windows, {})
    hits = []
    for t, rid in ctx.hits:
        if (t, rid) not in hits:
            hits.append((t, rid))
    return tier, [h for h in hits if h[0] == tier] or hits


def classify(command, pol, depth=None, windows=False):
    """Tier of a command line: the highest tier of its parts. The `depth` argument is kept for
    compatibility; nesting depth is MAX_DEPTH."""
    return classify_detail(command, pol, windows)[0]


# ---------------------------------------------------------------- hook entry point

def decide(payload, pol):
    """Return (exit_code, stdout_json_or_None, stderr_text)."""
    tool = payload.get("tool_name")
    if tool in WRITE_TOOLS:
        target = str(payload.get("tool_input", {}).get("file_path", payload.get("tool_input", {}).get("notebook_path", "")))
        tier = path_tier(target, pol)
        command = f"{tool} {target}"
    elif tool in SHELL_TOOLS:
        command = str(payload.get("tool_input", {}).get("command", ""))
        tier = classify(command, pol, windows=(tool == "PowerShell"))
    else:
        return 0, None, ""
    if tier == 3:
        return 2, None, f"Blocked (tier 3) by policy: {command[:120]}"
    if tier == 2:
        out = {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "ask",
                                      "permissionDecisionReason": f"Tier 2 (needs a human): {command[:120]}"}}
        return 0, json.dumps(out), ""
    return 0, None, ""


def main():
    try:
        payload = json.load(sys.stdin)
        pol = load_policy()
        code, out, err = decide(payload, pol)
        log = os.environ.get("AUDIT_LOG")
        if log and payload.get("tool_name") in SHELL_TOOLS + WRITE_TOOLS:
            ti = payload.get("tool_input", {})
            subject = str(ti.get("command", ti.get("file_path", ti.get("notebook_path", ""))))
            if payload["tool_name"] in WRITE_TOOLS:
                tier = path_tier(subject, pol)
            else:
                tier = classify(subject, pol, windows=(payload["tool_name"] == "PowerShell"))
            if tier >= 1:  # tier 1 allowed, tier 2 asked, tier 3 blocked: all are recorded
                sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
                import audit_chain
                audit_chain.append(log, "agent", f"tier{tier} decision (policy {pol['version']})", subject[:200])
    except Exception as exc:  # fail closed
        sys.stderr.write(f"Blocked: policy hook error ({type(exc).__name__}); failing closed\n")
        sys.exit(2)
    if out:
        sys.stdout.write(out)
    if err:
        sys.stderr.write(err + "\n")
    sys.exit(code)


if __name__ == "__main__":
    main()
