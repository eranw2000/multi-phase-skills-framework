#!/usr/bin/env python3
"""Tests for prune_stale_jobs. Run: python3 test_prune_stale_jobs.py

Every test asserts a CONTRAST (what is listed AND what is deliberately not), so a
matcher that lists everything, or nothing, goes red rather than passing vacuously.
The CLI is never called: each test hands in a fake runner.
"""
import io
import json
import os
import subprocess
import sys
from contextlib import redirect_stdout, redirect_stderr

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import prune_stale_jobs as P  # noqa: E402

DAY = 86400 * 1000
NOW = 1_790_000_000_000          # Unix milliseconds, like the CLI's startedAt
FAILURES = []


def check(name, cond, detail=''):
    if cond:
        print(f'  ok   {name}')
    else:
        print(f'  FAIL {name} {detail}')
        FAILURES.append(name)


def sess(id_, kind='background', state='blocked', days=30, name='x'):
    return {'id': id_, 'sessionId': id_ + '-s', 'cwd': '/tmp', 'kind': kind,
            'name': name, 'startedAt': NOW - days * DAY, 'state': state}


def runner(stdout='[]', rc=0, exc=None):
    def run(argv, **_kw):
        if exc:
            raise exc
        return subprocess.CompletedProcess(argv, rc, stdout=stdout, stderr='')
    return run


def run_main(argv, run):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        rc = P.main(argv, run=run, now_ms=NOW)
    return rc, out.getvalue(), err.getvalue()


def test_selection():
    sessions = [sess('old'), sess('young', days=3), sess('done', state='done'),
                sess('work', state='working'), sess('ia', kind='interactive', state=None),
                {'id': 'nostart', 'kind': 'background', 'state': 'blocked'}]
    ids = [s['id'] for s, _ in P.find_blocked(sessions, 14, NOW)]
    check('an old blocked background session is listed', 'old' in ids)
    check('a young one is not', 'young' not in ids)
    check('done and working are not', 'done' not in ids and 'work' not in ids)
    check('an interactive session is not', 'ia' not in ids)
    check('no start time is listed, age unknown', 'nostart' in ids)


def test_age_is_milliseconds():
    got = P.find_blocked([sess('a', days=20)], 14, NOW)
    check('startedAt read as ms gives 20 days', got and got[0][1] == 20, repr(got))
    check('threshold moves: 21 days hides it', P.find_blocked([sess('a', days=20)], 21, NOW) == [])


def test_report_prints_rm_lines_and_deletes_nothing():
    calls = []

    def run(argv, **kw):
        calls.append(argv)
        return subprocess.CompletedProcess(argv, 0, stdout=json.dumps([sess('abc123')]), stderr='')
    rc, out, _ = run_main([], run)
    check('exit 0', rc == 0)
    check('prints a claude rm line', 'claude rm abc123' in out, out)
    check('says nothing was removed', 'Nothing was removed' in out)
    check('only ever calls `claude agents --json`',
          calls == [['claude', 'agents', '--json']], repr(calls))


def test_unsafe_rows_get_no_rm_line():
    rows = [sess('good1'), {'id': 'nostart', 'kind': 'background', 'state': 'blocked'},
            sess('x; rm -rf ~'), sess('-rf'), sess('bad\nname', name='a\x1b[31mb')]
    rc, out, _ = run_main([], runner(json.dumps(rows)))
    check('exit 0', rc == 0)
    check('a normal id still gets a line', 'claude rm good1' in out, out)
    check('an unknown age gets no line', 'claude rm nostart' not in out, out)
    check('an id with shell text gets no line', 'claude rm x;' not in out, out)
    check('an option-shaped id gets no line', 'claude rm -rf' not in out, out)
    check('the skipped rows are explained', 'gets no removal line' in out, out)
    check('no control character reaches the output', '\x1b' not in out, repr(out))


def test_cli_failures_exit_2():
    for label, run in (('missing CLI', runner(exc=FileNotFoundError())),
                       ('non-zero exit', runner(rc=1)),
                       ('bad JSON', runner(stdout='not json')),
                       ('not a list', runner(stdout='{}'))):
        rc, out, err = run_main([], run)
        check(f'{label} exits 2 with a message', rc == 2 and 'Could not read' in err,
              f'rc={rc} err={err!r}')
    rc, out, _ = run_main([], runner(stdout='[]'))
    check('control: an empty list exits 0', rc == 0 and 'No blocked' in out)


def test_no_delete_path_left():
    src = open(os.path.join(HERE, 'prune_stale_jobs.py')).read()
    for word in ('rmtree', 'tarfile', 'state.json', '--apply', 'os.remove'):
        check(f'the script has no {word!r}', word not in src)


for fn in (test_selection, test_age_is_milliseconds,
           test_report_prints_rm_lines_and_deletes_nothing,
           test_unsafe_rows_get_no_rm_line,
           test_cli_failures_exit_2, test_no_delete_path_left):
    print(fn.__name__)
    fn()

print()
if FAILURES:
    print(f'FAILED: {len(FAILURES)} -> {FAILURES}')
    raise SystemExit(1)
print('all checks passed')
