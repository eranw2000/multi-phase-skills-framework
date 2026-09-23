#!/usr/bin/env python3
"""Report background sessions stuck in `blocked`, oldest first. It never deletes.

WHY THIS EXISTS
---------------
A background session whose work ended without a terminal signal rests in state
`blocked`, which Claude Code shows as "waiting on you", and nothing expires it. So
the list grows, and competes for attention with TODO.md, the real work queue.

Measured 2026-07-31: 36 sessions sat in `blocked`, the oldest two months old. 5 had
died on an API error, 3 were typos that never became work, and the rest were
briefings parked on their own closing offer. Exactly ONE carried a live action.

HOW IT READS THEM
-----------------
Through `claude agents --json`, the supported way for a script to read session
state, never through files under ~/.claude/jobs. Only `kind: background` sessions
count. The age is from `startedAt` (Unix milliseconds): the CLI has no last-activity
time, so the report says "started N days ago", which is not the same as idle.

REMOVING ONE
------------
This script prints a `claude rm <id>` line per session. Read the session first,
then run the line yourself, or press Ctrl+X twice on it in the agent view
(`claude agents`).

USAGE
    python3 prune_stale_jobs.py                  # 14-day default
    python3 prune_stale_jobs.py --older-than 30  # a different window
"""
import argparse
import json
import re
import subprocess
import sys
import time

MS_PER_DAY = 86400 * 1000


def load_sessions(run=subprocess.run):
    """The session list from `claude agents --json`, or raise RuntimeError."""
    try:
        p = run(["claude", "agents", "--json"], capture_output=True, text=True,
                timeout=60)
    except FileNotFoundError:
        raise RuntimeError("the `claude` command is not on PATH")
    except subprocess.TimeoutExpired:
        raise RuntimeError("`claude agents --json` did not answer within 60 seconds")
    if p.returncode != 0:
        raise RuntimeError("`claude agents --json` exited %d" % p.returncode)
    try:
        data = json.loads(p.stdout)
    except ValueError:
        raise RuntimeError("`claude agents --json` did not print JSON")
    if not isinstance(data, list):
        raise RuntimeError("`claude agents --json` did not print a list")
    return data


def find_blocked(sessions, older_than_days=14, now_ms=None):
    """[(session, age_days)] for background sessions in `blocked` that started at
    least `older_than_days` ago, oldest first. A session with no readable start time
    is listed with age None, since an unknown age is not a young one either."""
    now_ms = now_ms if now_ms is not None else time.time() * 1000
    out = []
    for s in sessions:
        if not isinstance(s, dict):
            continue
        if s.get("kind") != "background" or s.get("state") != "blocked":
            continue
        started = s.get("startedAt")
        if isinstance(started, (int, float)) and not isinstance(started, bool):
            age = int((now_ms - started) // MS_PER_DAY)
            if age < older_than_days:
                continue
        else:
            age = None
        out.append((s, age))
    out.sort(key=lambda t: -1 if t[1] is None else -t[1])
    return out


def main(argv=None, run=subprocess.run, now_ms=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--older-than", type=int, default=14, metavar="DAYS",
                    help="only list sessions that started at least this long ago (default 14)")
    args = ap.parse_args(argv)

    try:
        sessions = load_sessions(run)
    except RuntimeError as exc:
        print("Could not read the session list: %s." % exc, file=sys.stderr)
        return 2

    targets = find_blocked(sessions, args.older_than, now_ms)
    if not targets:
        print("No blocked background sessions started %d or more days ago." % args.older_than)
        return 0

    print("%d blocked background session(s) started %d or more days ago:"
          % (len(targets), args.older_than))
    for s, age in targets:
        name = printable(s.get("name"))[:56]
        started = "?" if age is None else "%dd" % age
        print("  %-10s %5s  %s" % (printable(s.get("id") or "?")[:10], started, name))
    removable = [s["id"] for s, age in targets
                 if age is not None and safe_id(s.get("id"))]
    print("\nNothing was removed.")
    if removable:
        print("To remove one after reading it:")
        for sid in removable:
            print("  claude rm %s" % sid)
    if len(removable) < len(targets):
        print("A session with no start time (?) or an unusual id gets no removal line. "
              "Look at it in `claude agents` first.")
    return 0


SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")


def safe_id(value):
    """True for an id that is safe to paste into a shell as printed."""
    return isinstance(value, str) and bool(SAFE_ID.match(value))


def printable(value):
    """The value as one line of text, with control characters made into spaces."""
    return "".join(c if c.isprintable() else " " for c in str(value or ""))


if __name__ == "__main__":
    raise SystemExit(main())
