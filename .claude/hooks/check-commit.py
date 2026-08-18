#!/usr/bin/env python3
"""PreToolUse gate for git commits and pushes.

Reads a Claude Code PreToolUse event on stdin. Denies the Bash call when a
commit message breaks the house convention `type(scope): description`, when a
commit tries to skip git hooks, when a push would force-overwrite the remote,
or when a push targets a protected branch. Stays silent otherwise so the
normal permission flow applies.
"""

import json
import re
import subprocess
import sys

TYPES = ("feat", "fix", "chore", "hotfix")
MAX_SUBJECT = 72

# Wrong type -> what to use instead.
ALIASES = {
    "refactor": "chore", "docs": "chore", "doc": "chore", "style": "chore",
    "test": "chore", "tests": "chore", "perf": "chore", "build": "chore",
    "ci": "chore", "deps": "chore", "revert": "chore", "wip": "chore",
    "feature": "feat", "feat!": "feat", "bugfix": "fix", "bug": "fix",
    "hot-fix": "hotfix", "hotfixes": "hotfix",
}

SUBJECT_RE = re.compile(
    r"^(?P<type>[A-Za-z][\w-]*)"
    r"(?:\((?P<scope>[^)]*)\))?"
    r"(?P<bang>!?)"
    r": ?(?P<desc>.*)$"
)
SCOPE_RE = re.compile(r"^[a-z0-9]+(?:[-.][a-z0-9]+)*$")
NON_IMPERATIVE = {
    "added", "fixed", "removed", "updated", "changed", "renamed", "bumped",
    "created", "deleted", "moved", "refactored", "implemented", "adds", "fixes",
    "removes", "updates", "changes", "renames", "bumps", "creates", "deletes",
    "adding", "fixing", "updating", "removing", "creating",
}

# Tokens that are common in French/Spanish/German and never appear in English,
# so they flag a description that wasn't translated. Deliberately excludes
# look-alikes such as "la", "est", "son", "met", "plus", "pas".
NON_ENGLISH = {
    "le", "les", "des", "une", "aux", "ses", "sont", "pour", "avec", "dans",
    "sur", "qui", "que", "cette", "ceux", "selon", "afin", "lors", "vers",
    "depuis", "toute", "toutes", "tous", "ajoute", "ajout", "corrige",
    "supprime", "suppression", "modifie", "permet", "gestion", "utilisateur",
    "utilisateurs", "fichier", "fichiers", "erreur", "erreurs", "mise",
    "affiche", "champ", "champs", "el", "los", "las", "para", "und", "der",
    "die", "nicht",
}

HELP = (
    "Required format: <type>(<scope>): <short description in English>\n"
    "  type   feat | fix | chore | hotfix\n"
    "  scope  the area worked on, lowercase kebab-case (auth, checkout, deps)\n"
    "  desc   English, imperative present, lowercase, no trailing period, "
    f"subject under {MAX_SUBJECT} chars"
)


def emit_deny(reason):
    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
        },
        sys.stdout,
    )
    sys.exit(0)


def allow():
    """No decision: the normal permission flow applies."""
    sys.exit(0)


def segments(command):
    """Split a shell command into rough subcommands (&&, ||, ;, |, newline)."""
    return [s.strip() for s in re.split(r"&&|\|\||[;\n|]", command) if s.strip()]


# --------------------------------------------------------------------------
# push
# --------------------------------------------------------------------------

BARE_FORCE = re.compile(r"(?:^|\s)(--force(?![-\w])|-f(?![-\w]))")
FORCE_REFSPEC = re.compile(r"(?:^|\s)\+[\w./-]+:[\w./-]+")
BROADCAST = re.compile(r"(?:^|\s)(--all|--mirror)(?![-\w])")

PROTECTED = {"main", "master"}

# `git push` options that swallow the next token as their value, so that token
# must not be mistaken for a remote or a refspec. Options taking an attached
# value (`--force-with-lease=...`, `--recurse-submodules=...`) don't belong
# here: their value never arrives as a separate token.
VALUE_OPTS = {"--repo", "-o", "--push-option"}


def current_branch(cwd):
    """Checked-out branch name, or None when it can't be determined."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=cwd or None,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def push_targets(seg, branch):
    """Branch names this `git push` segment would write to on the remote.

    `git push origin feat/x:main` targets `main`; a push with no refspec
    targets whatever branch is checked out.
    """
    tokens = seg.split()
    if "push" not in tokens:
        return []

    positional = []
    skip = False
    for token in tokens[tokens.index("push") + 1:]:
        if skip:
            skip = False
            continue
        if token in VALUE_OPTS:
            skip = True
            continue
        if token.startswith("-"):
            continue
        positional.append(token)

    # First positional is the remote; the rest are refspecs.
    refspecs = positional[1:]
    if not refspecs:
        return [branch] if branch else []

    targets = []
    for spec in refspecs:
        destination = spec.lstrip("+").split(":")[-1]
        destination = re.sub(r"^refs/heads/", "", destination)
        if destination in ("", "HEAD"):
            destination = branch
        if destination:
            targets.append(destination)
    return targets


def check_push(command, cwd):
    branch = None
    for seg in segments(command):
        if not re.search(r"\bgit\s+push\b", seg):
            continue
        if BARE_FORCE.search(seg):
            emit_deny(
                "`git push --force` is forbidden in this repo: it overwrites "
                "whatever is on the remote, including commits a teammate pushed "
                "while you were working.\n\n"
                "Use `git push --force-with-lease` instead. It does the same "
                "rewrite but refuses when the remote moved since your last "
                "fetch, so it can only ever discard your own work.\n\n"
                "If --force-with-lease is then rejected with 'stale info', stop "
                "and report it: run `git fetch` and show what arrived instead of "
                "escalating."
            )
        if FORCE_REFSPEC.search(seg):
            emit_deny(
                "A `+ref:ref` refspec is a force push in disguise and is "
                "forbidden. Use `git push --force-with-lease` if a rewrite is "
                "really what the user asked for."
            )
        if BROADCAST.search(seg):
            emit_deny(
                "`git push --all` / `--mirror` pushes every local branch, "
                f"including {' and '.join(sorted(PROTECTED))}. Push the current "
                "branch only: `git push` or `git push -u origin <branch>`."
            )

        if branch is None:
            branch = current_branch(cwd)
        for target in push_targets(seg, branch):
            if target in PROTECTED:
                emit_deny(
                    f"Pushing to `{target}` is forbidden in this repo. "
                    f"`{target}` only ever moves through a reviewed pull "
                    "request.\n\n"
                    "Push the work to its own branch instead:\n"
                    "  git switch -c <type>/<short-name>   # if still on "
                    f"{target}\n"
                    "  git push -u origin <branch>\n\n"
                    "Then open a PR. If the user insists on writing to "
                    f"{target} directly, stop and let them run the push "
                    "themselves."
                )
    allow()


# --------------------------------------------------------------------------
# commit
# --------------------------------------------------------------------------

HEREDOC_RE = re.compile(r"<<-?\s*['\"]?(?P<tag>[A-Za-z_][A-Za-z0-9_]*)['\"]?\r?\n(?P<body>.*?)\r?\n[ \t]*\1",
                        re.DOTALL)
DQ_MSG_RE = re.compile(r"(?:-m|--message=?)\s*\"(?P<msg>(?:[^\"\\]|\\.)*)\"")
SQ_MSG_RE = re.compile(r"(?:-m|--message=?)\s*'(?P<msg>[^']*)'")
BARE_MSG_RE = re.compile(r"(?:-m|--message=?)\s*(?P<msg>[^\s\"']\S*)")


def extract_message(command):
    """Return the commit message text, or None when it can't be read."""
    heredoc = HEREDOC_RE.search(command)
    if heredoc:
        return heredoc.group("body")
    for pattern in (DQ_MSG_RE, SQ_MSG_RE, BARE_MSG_RE):
        match = pattern.search(command)
        if match:
            return match.group("msg").replace('\\"', '"').replace("\\n", "\n")
    return None


def check_commit(command):
    commit_segs = [s for s in segments(command) if re.search(r"\bgit\s+commit\b", s)]
    if not commit_segs:
        allow()
    seg = commit_segs[0]

    if re.search(r"(?:^|\s)(--no-verify|-n(?![-\w]))", seg):
        emit_deny(
            "`--no-verify` is not allowed: it skips the repo's git hooks. If a "
            "hook is failing, report the failure and fix the cause instead of "
            "bypassing the check."
        )

    # An amend that reuses the existing message, or a commit that would open an
    # editor, has no message to inspect here.
    if re.search(r"--no-edit|--reuse-message|-C\b|--fixup|--squash", seg):
        allow()

    message = extract_message(command)
    if message is None:
        allow()

    lines = message.strip("\n").split("\n")
    subject = lines[0].strip()
    errors = []

    match = SUBJECT_RE.match(subject)
    if not match:
        emit_deny(
            f"Commit message rejected.\n\nSubject: {subject!r}\n"
            "It does not follow `type(scope): description`.\n\n" + HELP
        )

    ctype = match.group("type")
    scope = match.group("scope")
    desc = match.group("desc").strip()

    if ctype not in TYPES:
        suggestion = ALIASES.get(ctype.lower())
        hint = f" Use `{suggestion}` for this change." if suggestion else ""
        errors.append(
            f"type `{ctype}` is not allowed; pick one of "
            f"{', '.join(TYPES)}.{hint}"
        )
    if ctype != ctype.lower():
        errors.append(f"type must be lowercase (`{ctype.lower()}`, not `{ctype}`).")

    if scope is None:
        errors.append(
            "the scope is missing: name the area you worked on, as in "
            f"`{ctype.lower()}(auth): ...`."
        )
    elif not scope.strip():
        errors.append("the scope is empty.")
    elif "/" in scope:
        errors.append(
            f"scope `{scope}` is a path; use the module or feature name only "
            f"(`{scope.strip('/').split('/')[-1]}`)."
        )
    elif not SCOPE_RE.match(scope):
        errors.append(
            f"scope `{scope}` must be lowercase kebab-case, no spaces "
            "(auth, user-profile, deps)."
        )

    if not desc:
        errors.append("the description is empty.")
    else:
        first = desc.split()[0].lower().strip(",:;")
        if desc[0].isupper():
            errors.append(f"the description must start lowercase (`{desc[0].lower()}`).")
        if desc.endswith("."):
            errors.append("the description must not end with a period.")
        if first in NON_IMPERATIVE:
            errors.append(
                f"`{first}` is not imperative present; write `add`, not "
                "`added`/`adds`/`adding`."
            )
        if any(ord(char) > 127 for char in desc):
            errors.append(
                "the description must be written in English and plain ASCII."
            )
        foreign = sorted(
            {
                word
                for word in re.findall(r"[a-z']+", desc.lower())
                if word in NON_ENGLISH
            }
        )
        if foreign:
            errors.append(
                "the description must be in English; it looks like it isn't "
                f"({', '.join(foreign)}). Translate it, don't transliterate."
            )
        if len(desc.split()) < 2:
            errors.append(
                "the description says nothing on its own; describe the change, "
                "not the file."
            )

    if len(subject) > MAX_SUBJECT:
        errors.append(
            f"the subject line is {len(subject)} characters; keep it under "
            f"{MAX_SUBJECT}."
        )

    if len(lines) > 1 and lines[1].strip():
        errors.append("leave a blank line between the subject and the body.")

    if errors:
        bullets = "\n".join(f"  - {err}" for err in errors)
        emit_deny(
            f"Commit message rejected.\n\nSubject: {subject!r}\n\n{bullets}\n\n"
            + HELP
        )

    allow()


def main():
    try:
        event = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        allow()

    if event.get("tool_name") not in ("Bash", "PowerShell"):
        allow()

    command = (event.get("tool_input") or {}).get("command") or ""
    if re.search(r"\bgit\s+push\b", command):
        check_push(command, event.get("cwd"))
    if re.search(r"\bgit\s+commit\b", command):
        check_commit(command)
    allow()


if __name__ == "__main__":
    main()