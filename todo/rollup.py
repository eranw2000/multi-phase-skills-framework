#!/usr/bin/env python3
"""Cross-project rollup: every project's open Active-bucket items in one view.

Scans ~/.claude/projects/<X>/TODO.md (canonical dirs only), pulls the unchecked
top-level items from each file's Active bucket, flags due/overdue items against
today, and prints them grouped by project. Read-only — never edits anything.

Usage:
    python3 rollup.py [--due-soon-days N] [--today YYYY-MM-DD] [--all-buckets]

    --due-soon-days N   window (days) for the "due soon" flag (default 7)
    --today YYYY-MM-DD  override today's date (default: system date)
    --all-buckets       also list open items from Queued (not just Active)
"""

import argparse
import datetime
import re
from pathlib import Path

PROJECTS_DIR = Path.home() / ".claude" / "projects"
# The cross-project index lives in the dash-encoded home path
# (e.g. /Users/username -> "-Users-username"); derive it so this works on any machine.
INDEX_DIR = "-" + str(Path.home()).strip("/").replace("/", "-")

# Recognize a due date in several forms: canonical "(due 2026-05-29)", prose
# "Due 2026-05-29", "by 2026-05-29". Anchored on due/by + a small gap so incidental
# dates ("shipped 2026-05-27", "Started 2026-04-20") are not treated as deadlines.
DUE_RE = re.compile(r"(?i)\b(?:due|by)\b[^\d\n]{0,6}(\d{4}-\d{2}-\d{2})")
PIN_RE = re.compile(r">>>\s*NEXT SESSION")
# Heading line: capture level (# count) and text. Level 2 (##) = bucket boundary;
# level 3+ (###) = a work-area group WITHIN the current bucket, not a new bucket.
HEADING_RE = re.compile(r"^(#{2,6})\s*(?:\d+\.\s*)?([A-Za-z>].*)$")
# A top-level (non-indented) unchecked checkbox item.
OPEN_ITEM_RE = re.compile(r"^- \[ \]\s+(.+)$")
MAX_ITEM_LEN = 120


def canonical_todo_files():
    out = []
    for p in sorted(PROJECTS_DIR.iterdir()):
        if not p.is_dir() or p.name.startswith("-") or p.name == INDEX_DIR:
            continue
        todo = p / "TODO.md"
        if todo.exists():
            out.append((p.name, todo))
    return out


def bucket_keyword(heading_text):
    """First word of a bucket heading, lowercased (active, queued, parked, ...)."""
    return heading_text.strip().split()[0].lower() if heading_text.strip() else ""


def parse_open_items(todo_path, wanted_keywords):
    """Return (pin_text, [item lines]) for the wanted buckets."""
    try:
        lines = todo_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None, []

    pin = None
    items = []
    current_kw = None
    in_pin = False

    for line in lines:
        h = HEADING_RE.match(line)
        if h:
            level = len(h.group(1))
            heading_text = h.group(2)
            if PIN_RE.search(line):
                in_pin = True
                current_kw = None
                continue
            if level == 2:
                # A real bucket boundary.
                in_pin = False
                current_kw = bucket_keyword(heading_text)
            # level >= 3 is a work-area group inside the current bucket; leave
            # current_kw and in_pin untouched so its items still count.
            continue

        if in_pin:
            stripped = line.strip()
            if stripped and pin is None:
                pin = stripped
            continue

        if current_kw in wanted_keywords:
            m = OPEN_ITEM_RE.match(line)
            if m:
                items.append((current_kw, m.group(1).strip()))

    return pin, items


def flag(item_text, today, due_soon_days):
    m = DUE_RE.search(item_text)
    if not m:
        return ""
    try:
        due = datetime.date.fromisoformat(m.group(1))
    except ValueError:
        return ""
    delta = (due - today).days
    if delta < 0:
        return f"  [OVERDUE by {-delta}d]"
    if delta <= due_soon_days:
        return f"  [due in {delta}d]"
    return ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--due-soon-days", type=int, default=7)
    ap.add_argument("--today", default=None)
    ap.add_argument("--all-buckets", action="store_true")
    args = ap.parse_args()

    today = (datetime.date.fromisoformat(args.today)
             if args.today else datetime.date.today())
    wanted = {"active", "queued"} if args.all_buckets else {"active"}

    files = canonical_todo_files()
    shown = 0
    total_items = 0
    overdue = 0

    for name, todo in files:
        pin, items = parse_open_items(todo, wanted)
        if not items and not pin:
            continue
        shown += 1
        print(f"\n### {name}")
        if pin:
            print(f"  PIN: {pin}")
        for kw, text in items:
            f = flag(text, today, args.due_soon_days)
            if "OVERDUE" in f:
                overdue += 1
            total_items += 1
            prefix = "" if kw == "active" else f"[{kw}] "
            shown_text = text if len(text) <= MAX_ITEM_LEN else text[:MAX_ITEM_LEN - 1].rstrip() + "…"
            print(f"  - {prefix}{shown_text}{f}")

    print(f"\n---\n{total_items} open item(s) across {shown} project(s)"
          f" ({overdue} overdue). Today: {today.isoformat()}."
          f" Scanned {len(files)} project TODO file(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
