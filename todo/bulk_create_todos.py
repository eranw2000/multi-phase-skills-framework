#!/usr/bin/env python3
"""Bulk-create per-project TODO.md files across ~/.claude/projects/.

For every canonical project dir (non-dash-prefixed) that has no TODO.md, write one
from the shared 5-bucket template. Seed the Active bucket from the project's CLAUDE.md
where one exists (any "open items / next steps / pending work" style section); otherwise
write the empty template.

Never overwrites an existing TODO.md. Skips the cross-project index dir.

Usage:
    python3 bulk_create_todos.py [--dry-run] [--only <dirname>] [--date YYYY-MM-DD]

    --dry-run   print what would be created/seeded/skipped, write nothing
    --only      operate on a single project dir name (used by the todo skill to
                lazily create one file); still honors the skip-if-exists rule
    --date      synthesis date stamped into the header (default: today)
"""

import argparse
import datetime
import re
import sys
from pathlib import Path

PROJECTS_DIR = Path.home() / ".claude" / "projects"
# The cross-project index lives in the dash-encoded home path
# (e.g. /Users/username -> "-Users-username"); derive it so this works on any machine.
INDEX_DIR = "-" + str(Path.home()).strip("/").replace("/", "-")

# CLAUDE.md headings whose body we lift into the Active bucket as seed items.
# Word-boundary anchored so "## What NOT to do" doesn't match on a bare "to do".
SEED_HEADING_RE = re.compile(
    r"^#{1,6}\s.*?\b("
    r"planned enhancements|next steps|next session|open items|pending work|"
    r"potential next steps|todo|to-do"
    r")\b",
    re.IGNORECASE,
)

# A seeded line that is actually already finished (struck or DONE-tagged) — skip it.
DONE_MARKER_RE = re.compile(r"~~|\bDONE\b|✅|✔")

# A line that already looks like a checkbox or bullet item in the source section.
ITEM_RE = re.compile(r"^\s*(?:[-*+]\s+(?:\[[ xX]\]\s*)?|\d+\.\s+)(.+)$")


def canonical_project_dirs():
    """Every non-dash project dir except the index dir, sorted by name."""
    out = []
    for p in sorted(PROJECTS_DIR.iterdir()):
        if not p.is_dir():
            continue
        if p.name.startswith("-"):
            continue
        if p.name == INDEX_DIR:
            continue
        out.append(p)
    return out


def extract_seed_items(claude_md: Path, limit=15):
    """Pull bullet/numbered lines from any open-items-style section of CLAUDE.md.

    Returns a list of one-line strings (already stripped of the bullet prefix).
    """
    try:
        text = claude_md.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    lines = text.splitlines()
    items = []
    in_section = False
    section_heading_level = 0

    for line in lines:
        heading_match = re.match(r"^(#{1,6})\s", line)
        if heading_match:
            level = len(heading_match.group(1))
            if SEED_HEADING_RE.match(line):
                in_section = True
                section_heading_level = level
                continue
            # A heading at the same or higher level closes the seed section.
            if in_section and level <= section_heading_level:
                in_section = False
            continue

        if not in_section:
            continue

        m = ITEM_RE.match(line)
        if m:
            item = m.group(1).strip()
            # Drop empty husks, checked boxes, and anything already struck/DONE.
            checked = line.lstrip().startswith(("- [x]", "- [X]"))
            if item and not checked and not DONE_MARKER_RE.search(line):
                items.append(item)
        if len(items) >= limit:
            break

    return items


def build_todo(project_name, seed_items, date_str):
    """Render a per-project TODO.md from the canonical template."""
    if seed_items:
        synth = f"Per-project todo list. Synthesized {date_str} from this project's `CLAUDE.md`."
        active_block = "\n".join(f"- [ ] {it}" for it in seed_items)
    else:
        synth = f"Per-project todo list. Created {date_str} as a blank project todo list."
        active_block = ""

    index_dir = INDEX_DIR
    return f"""# {project_name} — TODO

{synth} Cross-linked from the global cross-project TODO at `~/.claude/projects/{index_dir}/TODO.md`.

Maintenance rule: when state moves, update this file AND the project `CLAUDE.md` (and the cross-project index) in the same turn.

State buckets (in order of relevance):
1. **Active — concrete next steps now**
2. **Queued — agreed, awaiting the user's go-ahead**
3. **Parked / on hold — don't propose unsolicited**
4. **Live (monitor only) — no action unless something breaks**
5. **Advisory — delivered, dormant unless re-engaged**

---

## 1. Active — concrete next steps now

{active_block}

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
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only", default=None, help="single project dir name")
    ap.add_argument("--date", default=None, help="synthesis date YYYY-MM-DD")
    args = ap.parse_args()

    date_str = args.date or datetime.date.today().isoformat()

    dirs = canonical_project_dirs()
    if args.only:
        dirs = [p for p in dirs if p.name == args.only]
        if not dirs:
            print(f"No canonical project dir named {args.only!r} (or it is the index dir).")
            return 1

    scanned = 0
    created_seeded = 0
    created_empty = 0
    skipped_existing = 0

    for p in dirs:
        scanned += 1
        todo_path = p / "TODO.md"
        if todo_path.exists():
            skipped_existing += 1
            continue

        claude_md = p / "CLAUDE.md"
        seed_items = extract_seed_items(claude_md) if claude_md.exists() else []
        content = build_todo(p.name, seed_items, date_str)

        if seed_items:
            created_seeded += 1
            tag = f"seed {len(seed_items)} item(s) from CLAUDE.md"
        else:
            created_empty += 1
            tag = "empty template"

        if args.dry_run:
            print(f"WOULD CREATE  {p.name}  ({tag})")
        else:
            todo_path.write_text(content, encoding="utf-8")
            print(f"CREATED       {p.name}  ({tag})")

    verb = "Would create" if args.dry_run else "Created"
    print()
    print(f"Scanned {scanned} canonical project dir(s) (index dir excluded).")
    print(f"Skipped (TODO.md already exists): {skipped_existing}")
    print(f"{verb}: {created_seeded + created_empty}  "
          f"(seeded from CLAUDE.md: {created_seeded}, empty: {created_empty})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
