# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

A training/sandbox repo ("claude-ci") whose real subject is the **agent tooling around the code** — the `@claude` GitHub workflow and the local commit hook — not the application. The app is a deliberately minimal Express server (`src/index.js`, two GET endpoints). Work here is usually about exercising the tooling end-to-end (open a PR, mention `@claude`, watch the action run) rather than shipping product code, so treat the app as a fixture: keep it small unless asked otherwise.

## Commands

```bash
npm install            # install deps
node src/index.js      # start the server on PORT (default 3000)
npm test               # NOT configured — exits 1 with "Error: no test specified"
```

There is no build, lint, or test tooling. If a task requires running or verifying tests, add the tooling first — do not assume `npm test` works.

## Application

`src/index.js` is the whole app: an Express instance serving `GET /hello` and `GET /goodbye`, listening on `process.env.PORT || 3000`.

Two loose ends worth knowing before touching it:

- `dotenv` is a dependency but is never required, so `.env` is not loaded and `PORT` only ever comes from the real environment. Wiring it up means adding `require('dotenv').config()` at the top of `src/index.js`.
- `.env.exemple` is committed but empty (and spelled the French way — keep the existing name rather than renaming it in passing). Mirror any new variable into it.

## CI: `.github/workflows/claude.yaml`

The single workflow runs `anthropics/claude-code-action@v1` when `@claude` appears in an issue body/title, an issue comment, a PR review, or a PR review comment. Details that trip people up:

- Authentication is `secrets.ANTHROPIC_API_KEY`. A failing run with no useful output is usually a missing or expired secret.
- `claude_args` pins `--model claude-haiku-4-5-20251001` and `--max-turns 20`. Both have been changed repeatedly in git history — check the current values before diagnosing "Claude stopped early".
- `--allowedTools` only permits `npm install`, `npm run build`, `npm run test:*`, `npm run lint:*`. Any other Bash command the CI agent tries is blocked. Adding a script that CI must run means adding it to this allowlist too.
- The inline `--system-prompt` says "Use TypeScript for new files" and "Ensure all new code has tests", which contradicts the repo (plain JS, no test runner). Treat it as stale config; if a task changes conventions, update this prompt in the same change.

## Local agent config: `.claude/`

`settings.json` registers a `PreToolUse` hook on every `git commit` and `git push`: `.claude/hooks/check-commit.py`. It denies the Bash call outright — this is not advisory, a malformed command simply will not run.

- **Commit messages** must be `type(scope): description` where type is one of `feat`, `fix`, `chore`, `hotfix` (no `refactor`/`docs`/`ci` — those are `chore`). Description in English, imperative present, lowercase, no trailing period, subject under 72 chars, at least two words.
- **Pushes** to `main` and `master` are refused in every form: explicit refspec, `HEAD:main`, a plain `git push` from a `main` checkout, branch deletion, and `--all` / `--mirror`. Those branches move only through a merged PR.
- `git push --force` / `-f` and `+ref:ref` refspecs are refused; use `--force-with-lease`. `git commit --no-verify` is refused.

`.claude/skills/commit/SKILL.md` is the long-form version of the same rules, invoked with `/commit`. It also states: no AI attribution or `Co-Authored-By` footer unless the user asks, and no merge, rebase, branch creation, or tag unless the user asks. When the two files disagree, they are meant to be changed together — the hook is what actually enforces.

## Conventions

- Work happens on feature branches (`feat/...`, `fix/...`) merged into `main` via PR; that is also how the `@claude` workflow gets exercised.
- `.gitignore` only covers `node_modules/`, so a real `.env` would be committed. Keep secrets out of the repo.
