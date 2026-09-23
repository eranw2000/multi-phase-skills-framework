#!/usr/bin/env python3
"""Report (and optionally prune) stale background jobs stuck in `blocked`.

WHY THIS EXISTS
---------------
A background job whose session ended without a terminal signal rests in state
`blocked` forever, and nothing expires it. That state is what Claude Code renders
as the "Needs input" list on the startup page, so it accumulates indefinitely and
competes for attention with TODO.md, which is the real work queue.

Measured 2026-07-31: 36 jobs sat in `blocked`, the oldest from 2026-05-29. Of those,
5 were jobs that had died on an API error (spend limit / 401 / usage policy), 3 were
typos that never became work, and the rest were briefings parked on their own closing
offer. Exactly ONE carried a live, uncaptured action. Every June job in the list was
`blocked` and none had a surviving transcript, while all 210 July jobs that reached a
terminal state were `done` with transcripts intact.

THE AGE THRESHOLD IS THE WHOLE DESIGN
-------------------------------------
Sweeping every blocked job would delete one the user was blocked on ten minutes ago. The
default of 14 days comes from that same cohort: it would have swept 32 of the 36
untouched while leaving the 4 most recent for review, and the single real loose end
was inside that recent window. So recent stays visible, archaeology goes.

USAGE
    python3 prune_stale_jobs.py                  # report only, 14-day default
    python3 prune_stale_jobs.py --older-than 30  # report, different window
    python3 prune_stale_jobs.py --apply          # archive, then delete

Deletion always archives first, to ~/.local/state/claude-jobs-archive/, and refuses
to delete unless every target is present in the archive it just wrote.
"""
import argparse
import datetime as dt
import glob
import json
import os
import shutil
import sys
import tarfile

JOBS_DIR = os.path.expanduser('~/.claude/jobs')
ARCHIVE_DIR = os.path.expanduser('~/.local/state/claude-jobs-archive')


def _parse_ts(value):
    """Parse an ISO-8601 stamp; return None if it is missing or unreadable."""
    if not value:
        return None
    try:
        return dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        return None


def find_blocked(jobs_dir=JOBS_DIR, older_than_days=14, now=None):
    """Return [(job_dir, state, age_days)] for blocked jobs past the age threshold.

    A job with no readable timestamp is reported with age None and is NEVER pruned:
    an unknown age must not be treated as an old one.
    """
    now = now or dt.datetime.now(dt.timezone.utc)
    out = []
    for path in sorted(glob.glob(os.path.join(jobs_dir, '*', 'state.json'))):
        try:
            with open(path) as fh:
                state = json.load(fh)
        except (OSError, ValueError):
            continue
        if state.get('state') != 'blocked':
            continue
        stamp = _parse_ts(state.get('updatedAt')) or _parse_ts(state.get('createdAt'))
        age = None if stamp is None else (now - stamp).days
        if age is not None and age < older_than_days:
            continue
        out.append((os.path.dirname(path), state, age))
    return out


def archive_and_remove(targets, archive_dir=ARCHIVE_DIR, jobs_dir=JOBS_DIR, stamp=None):
    """Tar every target, verify the tar holds all of them, then delete. Returns path."""
    if not targets:
        return None
    own = os.environ.get('CLAUDE_JOB_DIR', '')
    for job_dir, _, age in targets:
        # never walk outside the jobs dir, never delete the running job,
        # never delete something whose age we could not establish
        if os.path.dirname(os.path.abspath(job_dir)) != os.path.abspath(jobs_dir):
            raise SystemExit(f'refusing: {job_dir} is not directly under {jobs_dir}')
        if own and os.path.abspath(job_dir) == os.path.abspath(own):
            raise SystemExit('refusing to delete the job this session is running in')
        if age is None:
            raise SystemExit(f'refusing: {job_dir} has no readable timestamp')

    stamp = stamp or dt.date.today().isoformat()
    os.makedirs(archive_dir, exist_ok=True)
    # NEVER overwrite an existing archive. The name is only date-stamped, so a second
    # prune on the same day would otherwise destroy the first one's backup. (That is
    # not hypothetical: it happened on 2026-07-31 and cost the backup of 36 jobs.)
    tar_path = os.path.join(archive_dir, f'blocked-jobs-{stamp}.tar.gz')
    seq = 2
    while os.path.exists(tar_path):
        tar_path = os.path.join(archive_dir, f'blocked-jobs-{stamp}-{seq}.tar.gz')
        seq += 1
    with tarfile.open(tar_path, 'w:gz') as tf:
        for job_dir, _, _ in targets:
            tf.add(job_dir, arcname=os.path.basename(job_dir))

    with tarfile.open(tar_path) as tf:
        archived = {name.split('/')[0] for name in tf.getnames()}
    missing = [os.path.basename(d) for d, _, _ in targets
               if os.path.basename(d) not in archived]
    if missing:
        raise SystemExit(f'archive incomplete, refusing to delete: {missing}')

    for job_dir, _, _ in targets:
        shutil.rmtree(job_dir)
    return tar_path


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--older-than', type=int, default=14, metavar='DAYS',
                    help='only consider blocked jobs at least this old (default 14)')
    ap.add_argument('--apply', action='store_true',
                    help='archive and delete; without it this only reports')
    ap.add_argument('--jobs-dir', default=JOBS_DIR)
    args = ap.parse_args(argv)

    targets = find_blocked(args.jobs_dir, args.older_than)
    if not targets:
        print(f'No blocked jobs older than {args.older_than} days. Nothing to prune.')
        return 0

    print(f'{len(targets)} blocked job(s) older than {args.older_than} days:')
    for job_dir, state, age in targets:
        intent = (state.get('intent') or '').replace('\n', ' ')[:56]
        print(f"  {os.path.basename(job_dir):10} {age:>4}d  "
              f"{os.path.basename(state.get('cwd') or '?'):32} {intent}")

    if not args.apply:
        print('\nReport only. Re-run with --apply to archive and remove them.')
        print('Check the recent ones for a real pending ask before pruning.')
        return 0

    tar_path = archive_and_remove(targets)
    print(f'\nArchived {len(targets)} job dir(s) -> {tar_path}')
    print(f'Removed {len(targets)} job dir(s) from {args.jobs_dir}')
    left = find_blocked(args.jobs_dir, args.older_than)
    if left:
        print(f'WARNING: {len(left)} still present', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
