---
name: commit
description: Create git commits following the house convention `type(scope): short English description`, with types limited to feat, fix, chore and hotfix, and push them safely with --force-with-lease instead of --force. Use whenever the user asks to commit, to stage and commit changes, to write or fix a commit message, to split work into commits, to push, or invokes /commit.
disable-model-invocation: true
allowed-tools: Bash(git status *) Bash(git diff *) Bash(git add *) Bash(git commit *) Bash(git log *) Bash(git rev-parse *) Bash(git branch *) Bash(git push) Bash(git push origin *) Bash(git push -u *) Bash(git push --set-upstream *) Bash(git push --force-with-lease *)
---

# Commit

## Current repository state

- Branch and status: !`git status --short --branch`
- Staged diff: !`git diff --cached --stat`
- Unstaged diff: !`git diff --stat`
- Recent commits (house style reference): !`git log --oneline -10`

Read the full diffs with `git diff --cached` and `git diff` before writing a message. The `--stat` output above only tells you *where* the work happened, not *what* it does — the message has to describe the what.

## Message format

Always exactly this, on a single subject line:

```
<type>(<scope>): <short description in English>
```

### type

Pick one. Nothing else is allowed.

| type | Use for |
| --- | --- |
| `feat` | new behaviour a user or caller can observe |
| `fix` | correcting broken behaviour on the normal development flow |
| `chore` | everything with no behaviour change: deps, config, CI, tooling, formatting, renames, tests, docs |
| `hotfix` | an urgent fix going straight to production (hotfix branch, patch on a release tag, incident response) |

`fix` vs `hotfix` is about urgency and target, not size: same one-line correction is `fix` on a feature branch and `hotfix` when it ships to prod immediately. If the branch name or the user's wording doesn't make it clear, ask rather than guess.

### scope

The place the work happened, so a reader scanning `git log` knows which part of the system moved. Derive it from the changed paths: the package, module, folder, or feature name — `auth`, `checkout`, `api`, `user-profile`, `ci`, `deps`. Lowercase, kebab-case, one word when possible, never a full path (`auth`, not `src/modules/auth/services`).

If the change genuinely touches the whole repo (a global lint pass, a root config), use a broad scope such as `repo`, `config`, or `deps`. If it touches three or more unrelated areas, that is a signal to split it into several commits instead of inventing a vague scope.

### description

- English, always, even when the conversation is in another language.
- Imperative present: `add`, `remove`, `handle` — not `added`, `adds`, `adding`.
- Lowercase first letter, no trailing period.
- Describe the change, not the file: `fix(cart): prevent negative quantity on stock update`, not `fix(cart): update cart.ts`.
- Keep the whole subject line under 72 characters.

### body and footers (optional)

Add a body only when the *why* isn't obvious from the subject: a constraint, a trade-off, a workaround, a decision that will look wrong later without context. Blank line after the subject, wrap at 72 columns, bullets are fine.

Breaking change: `!` before the colon, plus a footer.

```
feat(api)!: return 422 instead of 400 on validation errors

BREAKING CHANGE: clients matching on status 400 must handle 422.
```

Reference issues in a footer when the user gives a number: `Refs: #142` or `Closes: #142`.

## Workflow

1. **Group before staging.** Read the diffs and decide how many commits the work is. One commit = one coherent change. A diff that mixes a feature and an unrelated dependency bump is two commits.
2. **When several commits are needed**, state the plan in one line each, then stage per commit with explicit paths (`git add src/auth/session.ts`) rather than `git add -A`. Never let one commit's files ride along in another.
3. **When one commit is enough** and nothing is staged yet, stage the relevant paths explicitly. Skip anything that shouldn't be versioned — `.env`, credentials, local scratch files, build output — and mention it instead of committing it.
4. **Commit** with a heredoc so multi-line messages keep their formatting:

   ```bash
   git commit -m "$(cat <<'EOF'
   fix(auth): reject expired refresh tokens

   The previous check compared against issue time, so a token stayed
   valid forever once refreshed.
   EOF
   )"
   ```

5. **Verify** with `git status` afterwards. If a pre-commit hook rewrote files, re-stage them and `git commit --amend --no-edit`. Never use `--no-verify` to get past a failing hook — report the failure instead.
6. **Push** once the commits are in, following the rules below. No branch creation, no tag, no merge, no rebase unless the user asks for it.

Never add AI attribution, `Co-Authored-By`, or a generated-with footer unless the user asks for it.

## Pushing

A normal push is `git push`, or `git push -u origin <branch>` the first time a branch goes up. Always push the current branch only — never `--all`, never an explicit refspec the user didn't ask for.

**Never push to `main` or `master`.** Those branches only ever move through a reviewed pull request, so no push may land on them — not a normal push, not a force push, not `origin main`, not `HEAD:main`, not a `--all` / `--mirror` that sweeps them up along the way, and not a deletion. This holds even when the user asks for it directly, and regardless of how small or urgent the change is.

Two cases in practice:

- **The work is already on a feature branch.** Push it and open a PR. `main` moves when the PR merges.
- **The commits landed on `main` locally.** Move them onto a branch before pushing anything:

  ```bash
  git switch -c fix/<short-name>   # takes the commits along
  git push -u origin fix/<short-name>
  ```

  Then reset the local `main` back onto its remote (`git switch main && git reset --hard origin/main`) only if the user asks — never on your own initiative.

If the user insists on writing to `main` directly, say once that the push is out of scope here and let them run it themselves. Don't work around it with a refspec, a rename, or a different remote.

**`--force` and `-f` are forbidden. Use `--force-with-lease` instead.** A plain force push overwrites whatever is on the remote, including a teammate's commits pushed while you were working; `--force-with-lease` refuses the push when the remote moved since your last fetch, so the overwrite can only ever destroy your own work. Same keystrokes, one class of accident removed.

```bash
git push --force-with-lease
```

If the user explicitly asks for `--force` or `-f`, run `--force-with-lease` instead and say so in one line. Don't argue about it, and don't ask for permission first — the substitution is the point of this rule.

When `--force-with-lease` is rejected (`stale info`), stop. Someone else pushed. Run `git fetch` and `git log --oneline origin/<branch>` to show what arrived, report it, and let the user decide between rebasing and abandoning the overwrite. Never escalate to `--force` to get past the rejection, and never `--force-with-lease` a shared branch (`develop`, `staging`, release branches) without the user asking for that branch by name. `main` and `master` are not on that list because no push reaches them at all.

A rewrite is only in scope when the user asked for one — after an `--amend`, an interactive rebase, or a squash. Don't rewrite history on your own initiative just to make a log look tidier.

## Examples

**Work:** added Google login to the auth module
→ `feat(auth): add Google OAuth sign-in`

**Work:** the cart total ignored discount codes over 50%
→ `fix(cart): apply discount codes above 50 percent`

**Work:** bumped React 18 → 19 and updated the lockfile
→ `chore(deps): upgrade react to 19`

**Work:** production is 500-ing because a config key is missing, patching the release branch now
→ `hotfix(config): add missing STRIPE_WEBHOOK_SECRET fallback`

**Work:** renamed variables and reformatted the invoice service, no behaviour change
→ `chore(invoicing): rename fields and reformat service`

**Work:** the endpoint now returns paginated results instead of a full list
→ `feat(api)!: paginate the /orders response` + `BREAKING CHANGE:` footer

## Anti-examples

| Wrong | Why |
| --- | --- |
| `fix: bug` | no scope, says nothing |
| `feat(auth): added login` | past tense; use `add` |
| `fix(panier): corrige le total` | must be English |
| `chore(src/modules/user/services): tidy up` | scope is a path, and "tidy up" isn't a change |
| `feat(app): add login, bump deps, fix typo` | three changes, three commits |
| `Feat(Auth): Add Login.` | capitals and trailing period |
| `refactor(auth): extract guard` | `refactor` isn't one of the four types — use `chore` |
| `git push --force` / `git push -f` | forbidden — use `git push --force-with-lease` |
| `git push --force-with-lease` after a `stale info` rejection | the remote moved: fetch, report, ask |
| `git push --all` | push the current branch only, and it would sweep up `main` |
| `git push origin main` / `git push` while on `main` | `main` moves through a PR only |
| `git push origin HEAD:master` | same push wearing a refspec |