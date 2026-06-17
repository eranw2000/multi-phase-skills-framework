# TODO.md format (shared protocol)

The canonical shape for every per-project `TODO.md` and for the cross-project index. Used by the `todo` skill (create + render + sync paths) and by `bulk_create_todos.py`. Keep all three consumers in step with this file.

## Where the files live

- **Per-project TODO.md:** `~/.claude/projects/<X>/TODO.md` (the project DATA dir, alongside the project `CLAUDE.md`). NOT the code repo.
- **Cross-project index:** `~/.claude/projects/<index-dir>/TODO.md` (the summary, one line per project). `<index-dir>` is the dash-encoded home path (e.g. `-Users-username` for `/Users/username`).
- **Memory:** all `project_*.md` files are centralized in `~/.claude/projects/<index-dir>/memory/`. No project dir has its own `memory/` subdir.

Link conventions (relative):
- per-project TODO.md to a memory file: `../<index-dir>/memory/project_*.md`
- index to a memory file: `memory/project_*.md`
- index to a per-project TODO.md: `../<X>/TODO.md`

## The five state buckets

In order of relevance. Every TODO.md uses this set. The bucket label after the dash is adaptable per project (e.g. "Parked / on hold" vs "Parked / contingent", "Queued v1.1"), but the five concepts and their order are fixed.

1. **Active — concrete next steps now**
2. **Queued — agreed, awaiting the user's go-ahead** (do not start unsolicited)
3. **Parked / on hold — don't propose unsolicited**
4. **Live (monitor only) — no action unless something breaks**
5. **Advisory — delivered, dormant unless re-engaged**

Not every project needs all five populated. An empty bucket can be dropped or left with a one-line "(none)".

## Item format

- Checkbox items: `- [ ] <one line>`. A finished item is struck, not deleted (see maintenance footer): `- [x] ~~<one line>~~`.
- One line per item plus a memory pointer. Do NOT duplicate detail that lives in the project `CLAUDE.md` or memory. The line is the index; the detail lives behind the link.

### Optional richer structure (use when a bucket earns it)

- **Work-area groups.** When a bucket holds several distinct streams, group items under a `### <heading>` with optional `Memory:` / `Repo:` / `Service:` pointer lines beneath the heading. New items go under the matching group; a bucket with no groups just lists items flat.
- **Bold lead-in.** Start an item with a short `**<lead-in>**` when it helps scanning (e.g. `- [ ] **OQ-1 production data feed:** ...`).
- **Sub-bullets.** Nest acceptance criteria or the concrete next sub-step under an item, indented two spaces. The parent stays a one-line index; the sub-bullets carry the checklist. Example:
  ```markdown
  - [ ] **Re-examine RECYCLE_RSS_MB by 2026-05-29 (after the next batch).** (due 2026-05-29)
    - Did oomKilled / 2Gi events stop?
    - What does idle rss settle to between jobs?
  ```
- **Due dates.** When writing, append `(due YYYY-MM-DD)` to an item line (machine-greppable; keep it even when a bold lead-in restates the date in prose). A condition with no fixed date stays in the prose ("after the next batch"); add `(due ...)` only once a real date exists. Flagging recognizes three forms — the canonical `(due ...)` suffix plus prose `Due YYYY-MM-DD` and `by YYYY-MM-DD` (both anchored on the keyword, so incidental dates like "shipped 2026-05-27" are not treated as deadlines) — so curated files that predate the suffix still surface as overdue without being rewritten.

### Pinned next-session marker

An optional pin block sits right after the maintenance-rule line, before "State buckets":

```markdown
## >>> NEXT SESSION: start here <<<

<the single most important thing to do next, one short paragraph or a few bullets>
```

Only one pin per file. Pinning replaces the block; unpinning removes it. (If a file's existing header uses an em dash, leave its exact text alone when editing that file. New pins use the colon form above to stay within the no-em-dash rule.)

## Full per-project template (seeded)

```markdown
# <Project> — TODO

Per-project todo list. Synthesized <DATE> from this project's `CLAUDE.md`. Cross-linked from the global cross-project TODO at `~/.claude/projects/<index-dir>/TODO.md`.

Maintenance rule: when state moves, update this file AND the project `CLAUDE.md` (and the cross-project index) in the same turn.

State buckets (in order of relevance):
1. **Active — concrete next steps now**
2. **Queued — agreed, awaiting the user's go-ahead**
3. **Parked / on hold — don't propose unsolicited**
4. **Live (monitor only) — no action unless something breaks**
5. **Advisory — delivered, dormant unless re-engaged**

---

## 1. Active — concrete next steps now

- [ ] <item>

## 2. Queued — agreed, awaiting go-ahead (do not start unsolicited)

## 3. Parked / on hold — don't propose unsolicited

## 4. Live (monitor only) — no action unless something breaks

## 5. Advisory — delivered, dormant unless re-engaged

---

## How to keep this file useful

- When you finish an item, strike it (don't delete on first pass — keep one session of history) and update the matching note in `CLAUDE.md`.
- When the user says "let's pick up X", move X to Active and write the first concrete next step.
- When state shifts, update this file AND the relevant `CLAUDE.md` entry AND the cross-project index in the same turn.
- Don't duplicate detail from `CLAUDE.md` here. One line per item plus a pointer is the target.
```

## Empty template (no CLAUDE.md to seed from)

Same as above, but the synthesis line reads `Created <DATE> as a blank project todo list.` and every bucket is empty (no items under Active).

## Auto-sync rule

Any change to a per-project TODO.md happens in the same turn as the matching updates to the two other artifacts:

1. **Per-project TODO.md** — the edit itself.
2. **Cross-project index** (`~/.claude/projects/<index-dir>/TODO.md`) — update the one-line entry for the project (a new Active item, or a status change that moves the project between buckets). One line plus the memory link; never copy the detail.
3. **Memory** (`~/.claude/projects/<index-dir>/memory/project_*<x>*.md`) — update the project memory's open-items / pending hook. If no memory file exists for the project, do NOT fabricate one; note that in the report and leave the link out (the index already does this for memory-less projects).
