#!/usr/bin/env python3
"""Tests for prune_stale_jobs. Run: python3 test_prune_stale_jobs.py

Every test asserts a CONTRAST (what is selected AND what is deliberately not),
so a matcher that selects everything, or nothing, goes red rather than passing
vacuously.
"""
import datetime as dt
import json
import os
import sys
import tarfile
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from prune_stale_jobs import find_blocked, archive_and_remove  # noqa: E402

NOW = dt.datetime(2026, 7, 31, tzinfo=dt.timezone.utc)
FAILURES = []

REAL_ARCHIVE = os.path.expanduser('~/.local/state/claude-jobs-archive')


def _snapshot_real_archive():
    """(name, size) for everything in the user's real archive dir, or None if absent."""
    if not os.path.isdir(REAL_ARCHIVE):
        return None
    return sorted((n, os.path.getsize(os.path.join(REAL_ARCHIVE, n)))
                  for n in os.listdir(REAL_ARCHIVE))


# taken at import, before any test has had a chance to write anything
REAL_BEFORE = _snapshot_real_archive()


def check(name, cond, detail=''):
    if cond:
        print(f'  ok   {name}')
    else:
        print(f'  FAIL {name} {detail}')
        FAILURES.append(name)


def make_job(root, jid, state, days_ago, intent='x', with_stamp=True):
    d = os.path.join(root, jid)
    os.makedirs(d)
    payload = {'state': state, 'intent': intent, 'cwd': f'/p/{jid}'}
    if with_stamp:
        stamp = (NOW - dt.timedelta(days=days_ago)).isoformat().replace('+00:00', 'Z')
        payload['updatedAt'] = stamp
    with open(os.path.join(d, 'state.json'), 'w') as fh:
        json.dump(payload, fh)
    return d


def test_selection():
    with tempfile.TemporaryDirectory() as root:
        make_job(root, 'old_blocked', 'blocked', 40)
        make_job(root, 'edge_blocked', 'blocked', 14)
        make_job(root, 'recent_blocked', 'blocked', 5)
        make_job(root, 'old_done', 'done', 40)
        make_job(root, 'old_failed', 'failed', 40)
        make_job(root, 'working', 'working', 40)
        found = {os.path.basename(d) for d, _, _ in find_blocked(root, 14, NOW)}

        # selected
        check('selects a 40-day blocked job', 'old_blocked' in found)
        check('selects exactly at the threshold (14d)', 'edge_blocked' in found)
        # contrast: these must NOT be selected
        check('skips a 5-day blocked job', 'recent_blocked' not in found,
              '(recent asks must stay visible)')
        check('skips done', 'old_done' not in found)
        check('skips failed', 'old_failed' not in found)
        check('skips working', 'working' not in found)
        check('selected exactly 2', len(found) == 2, f'got {sorted(found)}')


def test_threshold_moves():
    with tempfile.TemporaryDirectory() as root:
        make_job(root, 'j20', 'blocked', 20)
        check('20d job absent at --older-than 30',
              not find_blocked(root, 30, NOW))
        check('20d job present at --older-than 10',
              len(find_blocked(root, 10, NOW)) == 1)


def test_missing_timestamp_reported_never_pruned():
    with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as arc:
        make_job(root, 'nostamp', 'blocked', 0, with_stamp=False)
        targets = find_blocked(root, 14, NOW)
        check('a stampless blocked job is reported', len(targets) == 1)
        check('its age is None, not 0', targets[0][2] is None)
        try:
            archive_and_remove(targets, archive_dir=arc, jobs_dir=root)
            check('refuses to delete a stampless job', False, '(it deleted it)')
        except SystemExit:
            check('refuses to delete a stampless job', True)
        check('the stampless job still exists',
              os.path.isdir(os.path.join(root, 'nostamp')))


def test_archive_completeness_then_delete():
    with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as arc:
        make_job(root, 'a1', 'blocked', 30)
        make_job(root, 'a2', 'blocked', 30)
        targets = find_blocked(root, 14, NOW)
        tar_path = archive_and_remove(targets, archive_dir=arc, jobs_dir=root,
                                      stamp='test')
        with tarfile.open(tar_path) as tf:
            names = {n.split('/')[0] for n in tf.getnames()}
        check('archive holds both jobs', {'a1', 'a2'} <= names, f'got {names}')
        check('both dirs are gone',
              not os.path.isdir(os.path.join(root, 'a1'))
              and not os.path.isdir(os.path.join(root, 'a2')))
        check('archive file is non-empty', os.path.getsize(tar_path) > 0)


def test_refuses_path_outside_jobs_dir():
    with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as other, \
            tempfile.TemporaryDirectory() as arc:
        stray = os.path.join(other, 'nested', 'deep')
        os.makedirs(stray)
        targets = [(stray, {'state': 'blocked'}, 30)]
        try:
            archive_and_remove(targets, archive_dir=arc, jobs_dir=root)
            check('refuses a dir outside jobs/', False, '(it proceeded)')
        except SystemExit:
            check('refuses a dir outside jobs/', True)
        check('the stray dir survives', os.path.isdir(stray))


def test_never_overwrites_an_existing_archive():
    """A second prune on the same day must not destroy the first one's backup."""
    with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as arc:
        make_job(root, 'first', 'blocked', 30)
        p1 = archive_and_remove(find_blocked(root, 14, NOW), archive_dir=arc,
                                jobs_dir=root, stamp='same-day')
        size1 = os.path.getsize(p1)
        make_job(root, 'second', 'blocked', 30)
        p2 = archive_and_remove(find_blocked(root, 14, NOW), archive_dir=arc,
                                jobs_dir=root, stamp='same-day')
        check('the second archive gets a distinct path', p1 != p2, f'{p1} == {p2}')
        check('the first archive still exists', os.path.exists(p1))
        check('the first archive is unchanged', os.path.getsize(p1) == size1)
        with tarfile.open(p1) as tf:
            first_names = {n.split('/')[0] for n in tf.getnames()}
        with tarfile.open(p2) as tf:
            second_names = {n.split('/')[0] for n in tf.getnames()}
        check('the first archive still holds its own job', 'first' in first_names)
        check('the second holds the second job', 'second' in second_names)
        check('the second did not swallow the first', 'first' not in second_names)


def test_never_writes_to_the_real_archive_dir():
    """Guards the mistake that destroyed the 2026-07-31 backup: a call that omits
    archive_dir falls through to the user's REAL archive location.

    Asserted directly rather than by counting call sites in this file's own source.
    A textual count is brittle (it miscounts its own literals) and would keep passing
    if a future call site were added with the argument spelled differently.
    REAL_BEFORE is snapshotted at import, before any test has run.
    """
    check('the real archive dir is untouched by this suite',
          _snapshot_real_archive() == REAL_BEFORE,
          f'{REAL_BEFORE} -> {_snapshot_real_archive()}')


for fn in (test_selection, test_threshold_moves,
           test_missing_timestamp_reported_never_pruned,
           test_archive_completeness_then_delete,
           test_refuses_path_outside_jobs_dir,
           test_never_overwrites_an_existing_archive,
           test_never_writes_to_the_real_archive_dir):
    print(fn.__name__)
    fn()

print()
if FAILURES:
    print(f'FAILED: {len(FAILURES)} -> {FAILURES}')
    raise SystemExit(1)
print('all checks passed')
