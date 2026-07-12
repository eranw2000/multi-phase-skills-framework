---
model: sonnet
name: todo
description: Persistent markdown todo manager for projects. Reads and edits the per-project TODO.md in the project data dir (~/.claude/projects/<X>/TODO.md) and keeps the cross-project index and project memory in sync. Use when the user says "todo", "/todo", "what's on the todo list", "add a todo", "mark X done", "what's open on this project", or "move X to parked/queued". This is the PERSISTENT markdown todo, NOT Claude Code's built-in ephemeral TodoWrite task tracker.
argument-hint: "[list | all | add <text> [bucket] [due <date>] | done <text> | move <text> <bucket> | pin <text> | unpin | sync]"
---

# Todo (persistent markdown todo manager)

Manage a project's open work in a `TODO.md` file that survives across sessions. Each project has one at `~/.claude/projects/<X>/TODO.md`, organized into the five state buckets. A cross-project index at `~/.claude/projects/<index-dir>/TODO.md` rolls them up, one line per project. The `<index-dir>` is the dash-encoded home path (e.g. `-Users-username` for `/Users/username`); the helper scripts derive it automatically.

**This is NOT Claude Code's built-in TodoWrite tool.** TodoWrite is an ephemeral in-session task tracker that vanishes when the session ends. This skill edits real markdown files on disk. Never call TodoWrite to satisfy a `/todo` request, and never edit these files via TodoWrite.

The canonical file shape, the five buckets, the link conventions, and the auto-sync rule all live in `todo-format.md` (alongside this file, at `~/.claude/skills/todo/todo-format.md`). Read it before editing any TODO.md.

## Step 1 — Resolve the current project

Determine which project this is, in order (same algorithm `save-context` uses):
1. If cwd is inside `~/.claude/projects/<X>/`: project = `<X>`.
2. If cwd is inside a git repo (`REPO_ROOT=$(git rev-parse --show-toplevel)`): take the repo basename, then match it against `~/.claude/projects/` by NAME — the folder is sometimes prefixed (e.g. `Python-Project-<base>`) and does NOT always equal the repo name. Run `find ~/.claude/projects -maxdepth 1 -type d \( -name '<base>' -o -name 'Python-Project-<base>' \)`. Never string-build the path and assume it exists.
3. If cwd is a dash-prefixed leftover folder: use the trailing `<Name>` segment.
4. Zero or multiple matches, or cwd is bare `~/.claude`: list `ls -lt ~/.claude/projects` (top 4 most recent) and ASK the user which project. Do not guess.

State the resolved project in one sentence, then proceed. The target file is `~/.claude/projects/<X>/TODO.md`.

If the file doesn't exist, create it first from the template in `todo-format.md` (seed from the project `CLAUDE.md` if one exists — reuse `bulk_create_todos.py`'s seeding by running it for the single dir, or write the empty template inline).

## Step 2 — Dispatch on `$ARGUMENTS`

Empty arguments default to `list`.

- **`list` / `status`** (read-only): render the buckets the file actually has, with their open items (usually the canonical five, but honor any extra or renamed buckets a curated file uses). Render the pin block first if present. Lead with the project name and a one-line count summary (e.g. "5 active, 2 queued, 1 parked"). **Surface due dates:** for any item carrying a due date — the canonical `(due YYYY-MM-DD)` suffix, or a prose `Due YYYY-MM-DD` / `by YYYY-MM-DD` form (anchored on "due"/"by", not an incidental date like "shipped 2026-05-27") — annotate it in your rendered output against today's date: `OVERDUE` if past, `due in Nd` if within 7 days. The annotation is for the rendered view only; do not write it into the file. No sync needed.
- **`all` / `status all`** (read-only, cross-project): run `python3 ~/.claude/skills/todo/rollup.py` and present its output — every project's open Active items, with overdue/upcoming flags, grouped by project. This is the "what's open / what's next" view across all projects. Does not edit any file. (To refresh the curated index file itself, see Step 4's index note, but `all` only reads.)
- **`add <text> [bucket] [due <date>]`**: add `- [ ] <text>` to the named bucket (default **Active**). If a due date is given, append `(due YYYY-MM-DD)`. If the bucket uses work-area `###` groups, place the item under the matching group (ask or create one only if none fits) rather than dropping it loose. Then auto-sync.
- **`done <text>`**: find the matching item, strike it — `- [x] ~~<text>~~` — don't delete it (keep one session of history per the maintenance footer). Then auto-sync.
- **`move <text> <bucket>`**: relocate the item to the named bucket. Then auto-sync.
- **`pin <text>`**: write `<text>` into the pin block (`## >>> NEXT SESSION: start here <<<`) right after the maintenance-rule line, creating the block if absent and replacing its contents if present. One pin per file. If the file already has a `>>> NEXT SESSION — start here <<<` style header, update that block in place rather than adding a second. No cross-project sync needed for a pin (it's local focus), though you may note it in the report.
- **`unpin`**: remove the pin block.
- **`sync`**: run the three-way sync only (Step 4), no item edit. Use after manual TODO.md edits.

Match `<text>` against existing items by substring, case-insensitive. If it matches none (for done/move) or several ambiguously, ask which one rather than guessing. Today's date is available in the session context; use it for due-date math.

## Step 3 — Edit the per-project TODO.md

Apply the mutation using the format in `todo-format.md`: one line per item, memory pointer not detail, strike-don't-delete on completion. The file content follows plain-prose writing (no em dashes, no AI-typical vocabulary) and uses no Unicode box-drawing characters.

**Preserve a file's existing structure.** Some files are hand-curated and use different bucket labels (e.g. "Parked / contingent") or extra buckets ("Backlog", "Future / discussed", a ">>> NEXT SESSION" header). Edit items inside whatever structure is already there. Never rename, reorder, merge, or drop an existing file's buckets to match the canonical template, and never restyle its header or footer. The canonical 5-bucket template applies only when CREATING a new file. For `add` to a bucket that doesn't exist in that file, use the closest existing bucket (e.g. "Parked" → "Parked / contingent") rather than inventing the canonical one alongside it.

## Step 4 — Auto-sync (after any mutating mode)

In the same turn, per `todo-format.md`:
1. **Per-project TODO.md** — already edited in Step 3.
2. **Cross-project index** (`~/.claude/projects/<index-dir>/TODO.md`) — find the project's section or one-line entry; update it for a new Active item or a status change that moves the project between buckets. One line plus the memory link. If the project has no entry yet and the change is Active-bucket work, add a one-line entry under the right bucket.
3. **Memory** — `find ~/.claude/projects/<index-dir>/memory -iname 'project_*<x>*.md'` (lowercased, fuzzy on the project name). One clear match: update its open-items / pending hook. Several topic-split files: pick the one whose topic matches the item. No match: do NOT fabricate a memory file; note "no project_*.md memory yet" in the report and skip this leg.

## Step 5 — Report

State tightly what changed across the three artifacts: the per-project edit, the index line (or "no index change"), and the memory update (or "no memory file"). For `list`, just render the buckets.

## Guardrails

- Persistent markdown todo, not TodoWrite. Never conflate the two.
- One line per item plus a memory pointer. Never copy `CLAUDE.md` or memory detail into the todo line.
- Strike, don't delete, on first completion — keep one session of history.
- Quote all paths (some project dirs have spaces in their names).
- When resolution is ambiguous, ask. A wrong-project edit is a real mistake.
