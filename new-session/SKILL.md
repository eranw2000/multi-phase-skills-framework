---
name: new-session
description: Start-of-session briefing for a project — context-window usage reminder, the project's open TODO items, and open action items not yet tracked in the TODO. Use when sitting back down on a project after time away, or when the user says "new session", "where was I", "catch me up", "what's the state", "what's open", or "/new-session". Read-only; never commits, pushes, deploys, or edits files.
disable-model-invocation: false
argument-hint: "[project name] (optional; defaults to the current directory's project)"
---

# Start-of-Session Briefing

Give the developer a fast read on where a project stands when they sit back down on it. Produce a single session-start briefing with three parts, in this order. This skill is **read-only**: inspect and report, never commit, push, deploy, or edit files. The one allowed mutation is offered (not performed) at the very end: adding the uncaptured items to `TODO.md`, and only if the user says yes.

If `$ARGUMENTS` names a project, orient on that one. Otherwise resolve from the current directory (see Setup).

## Part 1: Context window usage (manual)

`/context` is a built-in command. A skill cannot trigger it, so this part can't be automated. Make your **first line of output**:

> Run `/context` to see your context-window token usage. Built-in commands can't be auto-invoked from a skill, so type it yourself.

Then stop on Part 1 and move on. Do not guess a token count; you have no reliable way to measure the window.

## Setup: resolve the project (do this before Parts 2 and 3)

Use the same algorithm the `todo` and `save-context` skills use. In order, stop at the first hit:

1. If `$ARGUMENTS` is non-empty, treat it as the project name and match it under `~/.claude/projects/` by name (the folder is sometimes prefixed, e.g. `Python-Project-<base>`): `find ~/.claude/projects -maxdepth 1 -type d \( -iname '<arg>' -o -iname 'Python-Project-<arg>' -o -iname '*<arg>*' \)`.
2. Else if cwd is inside `~/.claude/projects/<X>/`: project = `<X>`.
3. Else if cwd is inside a git repo (`REPO_ROOT=$(git rev-parse --show-toplevel)`): take the repo basename, then match it against `~/.claude/projects/` by NAME with the same `find` as step 1 (the folder name frequently does NOT equal the repo name). Never string-build the project path and assume it exists.
4. Zero or multiple matches, or cwd is bare `~/.claude`: list `ls -lt ~/.claude/projects` (top 5) and ASK which project. Do not guess.

State the resolved project, the path to its `TODO.md` (`~/.claude/projects/<X>/TODO.md`), and its `CLAUDE.md` (repo-root first, then `~/.claude/projects/<X>/CLAUDE.md`) in one line. Also capture `REPO_ROOT` if a linked repo is found; Part 3 needs it for the git/PR sweep.

The cross-project memory and index live under a dash-encoded home directory, `~/.claude/projects/<index-dir>/`, where `<index-dir>` is the user's home path with slashes turned into dashes (e.g. `-Users-jdoe` for `/Users/jdoe`). Derive it from `$HOME` rather than hard-coding it; Part 3 uses it to find the project memory files.

## Part 2: Open TODO items (this project)

Read `~/.claude/projects/<X>/TODO.md`. Render the **open** (unchecked `- [ ]`) items, grouped by the buckets the file actually uses (honor any non-canonical bucket labels or extra buckets a curated file has; render a pin block first if present). Lead with a one-line count summary (e.g. "3 active, 1 queued, 1 parked"). Skip struck/`- [x]` items.

Surface due dates against today's date (today is in the session context): annotate `OVERDUE` if past, `due in Nd` if within 7 days. Recognize the `(due YYYY-MM-DD)` suffix and prose `Due YYYY-MM-DD` / `by YYYY-MM-DD` forms. The annotation is for display only; do not write it into the file.

If no `TODO.md` exists, say so and note it can be created with the `todo` skill. The format reference is `~/.claude/skills/todo/todo-format.md`.

## Part 3: Open action items NOT in the TODO list

Sweep the sources below for open/pending work, then **reconcile against Part 2**: drop anything already represented in `TODO.md` (substring or clear semantic match) and present only what is uncaptured. The goal is to catch loose ends the TODO doesn't know about. Run the read-only commands in parallel where possible; tolerate missing tools (skip a source silently if its tool/file is absent).

1. **Project CLAUDE.md**: scan for pending work in sections like "Still blocked", "Open questions", "Next steps", "Deferred", "TODO", and any gotcha that names an unresolved action. Pull the open ones.
2. **Project memory**: `~/.claude/projects/<index-dir>/memory/project_*.md` files for this project: any "awaiting", "blocked on", "pending", or unfinished-decision items. (Skip if the memory folder does not exist.)
3. **Git working state** (if `REPO_ROOT`): `git status --porcelain` (uncommitted/staged work in flight), `git rev-list --left-right --count HEAD...main` (commits ahead means unpushed/unreleased work), `git stash list` (forgotten stashes). Use the repo's actual default branch if it isn't `main`.
4. **Open PRs** (if `gh` is authed and a remote exists): `gh pr list --base main --state open --json number,title,isDraft,createdAt`. Flag PRs older than 14 days as stale.
5. **OpenSpec changes** (if `openspec/changes/` exists): changes with incomplete tasks (unchecked items in their `tasks.md`).
6. **Spec-review blockers** (if a `COMMENTS.md` exists): unresolved items in the Blocker band.
7. **Code markers** (optional, repo only): a count of `TODO`/`FIXME`/`XXX` markers via `grep -rInE '\b(TODO|FIXME|XXX)\b'` excluding `.venv`/`node_modules`/`.git`. Report the count, do not dump them, unless one obviously names a near-term action.

Present these under a clear heading like "Open, not tracked in TODO.md" with the source noted per item (e.g. `[PR #12]`, `[CLAUDE.md: Still blocked]`, `[git: 2 commits ahead]`). If everything open is already in the TODO, say so plainly.

## Output shape

Keep it scannable and short, one screen if possible:

1. The `/context` reminder line (Part 1).
2. Resolved project and file paths (one line).
3. **In TODO**: open items by bucket, with due-date flags.
4. **Open, not in TODO**: uncaptured items with source tags, or "nothing uncaptured".
5. A closing line: if Part 3 found uncaptured items, offer to add them to `TODO.md` via the `todo` skill (ask first; do not add unprompted). Otherwise suggest the single most sensible next action based on what you found.

Do not pad the briefing with restated CLAUDE.md detail; link or point rather than copy. Follow plain-prose conventions (no em dashes in your own prose, no box-drawing characters in any table).
