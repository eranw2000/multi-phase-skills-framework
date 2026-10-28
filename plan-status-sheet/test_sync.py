#!/usr/bin/env python3
"""Checks for the plan-status engine. Offline: no token, no network, no writes.

EVERY CHECK HERE IS PAIRED WITH A CONTROL that must fire. A guard that only ever sees
good input looks identical to a guard that cannot fail, and this file exists to tell
those two apart.

    python3 test_sync.py
"""
import ast
import collections
import importlib.util
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("sync", HERE / "sync.py")
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)

FAILS = []


def check(name, got, want):
    ok = got == want
    print(("  OK   " if ok else "  FAIL ") + name
          + ("" if ok else f"   got={got!r} want={want!r}"))
    if not ok:
        FAILS.append(name)


class FakeReport:
    def __init__(self):
        self.failures, self.warnings, self.lines = [], [], []

    def note(self, t): self.lines.append(t)
    def item(self, t): self.lines.append(t)
    def count(self, label, n): self.lines.append(f"{label}: {n}")
    def warn(self, t): self.warnings.append(t)
    def fail(self, t): self.failures.append(t)


class FakeConfig:
    SECTIONS_WITHOUT_ROWS = {}


class FakeData:
    STATUS_STYLE = {"Live": ("FF1E7A3C", "FFFFFFFF"),
                    "Not started": ("FFF2F2F2", "FF595959")}
    PHASE_BUDGET = {"Phase 1": "3-5 days"}


class FakeProject:
    def __init__(self, rows, plan=None, excused=None):
        self._rows = rows
        self.headers = list(sync.BASE_HEADERS)
        self.plan_path = plan
        self.data = FakeData()
        self.config = FakeConfig()
        self.config.SECTIONS_WITHOUT_ROWS = excused or {}

    @property
    def rows(self):
        return [list(r) for r in self._rows]

    @property
    def status_style(self):
        """Mirrors the real Project: the data module's map if it has one, else the
        skill's default. The double has to carry this or it stops standing in for the
        thing under test."""
        return dict(getattr(self.data, "STATUS_STYLE", None) or sync.DEFAULT_STATUS_STYLE)


def row(section="4.1", feature="A feature", status="Live", date="2026-01-01",
        depends="None", phase="Phase 1", effort="2 days"):
    return [section, feature, "does a thing", status, date, depends, phase,
            "3-5 days", effort, "stands here"]


# ------------------------------------------------------------- a fake Sheets service
#
# It records every request and answers reads from what was written, the way the real
# API does with UNFORMATTED_VALUE: numbers come back as numbers and trailing empty
# cells are left off. Nothing here reaches Google.

class _Exec:
    def __init__(self, fn):
        self.fn = fn

    def execute(self):
        return self.fn()


def _sent_value(c):
    uv = c["userEnteredValue"]
    if "numberValue" in uv:
        n = uv["numberValue"]
        return int(n) if float(n).is_integer() else n
    return uv["stringValue"]


def _tab_of(a1):
    tab = a1.rsplit("!", 1)[0]
    if tab.startswith("'") and tab.endswith("'"):
        tab = tab[1:-1].replace("''", "'")
    return tab


class FakeSvc:
    def __init__(self, markers=(), tabs=("Plan status", "Summary"), read_error=None,
                 meta_error=None, corrupt=None):
        self.markers = list(markers)
        self.tabs = {name: i for i, name in enumerate(tabs)}
        self.read_error, self.meta_error, self.corrupt = read_error, meta_error, corrupt
        self.batches, self.ranges, self.written = [], [], {}

    def spreadsheets(self):
        svc = self

        class Values:
            def get(self, spreadsheetId, range, **kw):  # noqa: A002 - the API's name
                return _Exec(lambda: svc.read(range))

        class Sheets:
            def get(self, spreadsheetId, **kw):
                return _Exec(svc.meta)

            def batchUpdate(self, spreadsheetId, body):
                return _Exec(lambda: svc.batch(body))

            def values(self):
                return Values()
        return Sheets()

    def meta(self):
        if self.meta_error:
            raise self.meta_error
        return {"sheets": [{"properties": {"title": t, "sheetId": i}}
                           for t, i in self.tabs.items()],
                "developerMetadata": [{"metadataKey": sync.MARKER_KEY, "metadataValue": m,
                                       "location": {"spreadsheet": True}}
                                      for m in self.markers]}

    def batch(self, body):
        self.batches.append(body)
        for req in body["requests"]:
            if "updateCells" in req:
                uc = req["updateCells"]
                self.written[uc["start"]["sheetId"]] = [
                    [_sent_value(c) for c in r["values"]] for r in uc["rows"]]
        return {"replies": []}

    def read(self, a1):
        self.ranges.append(a1)
        tab = _tab_of(a1)
        rows = [list(r) for r in self.written.get(self.tabs.get(tab), [])]
        if a1.endswith("A4:ZZ4"):
            if self.read_error:
                raise self.read_error
            return {"values": rows[3:4]} if len(rows) > 3 else {}
        if self.corrupt and self.corrupt[0] == tab:
            _, r, c = self.corrupt
            rows[r][c] = "SOMEBODY CHANGED THIS"
        for r in rows:
            while r and r[-1] == "":
                r.pop()
        return {"values": rows}

    def wrote_cells(self):
        return any("updateCells" in req for b in self.batches for req in b["requests"])


def _demo_project(root, name="demo-project", data_extra="", config_extra="",
                  sid="SID_DEMO"):
    import json as _json
    demo = root / name
    demo.mkdir()
    (demo / sync.CONFIG_NAME).write_text(
        'DATA_MODULE = "rows.py"\nPLAN = None\nDOC_TITLE = "demo: plan status"\n'
        'PINNED_CELL = ("A feature", 3, "Live")\nREPO = None\n' + config_extra)
    (demo / "rows.py").write_text(
        'ROWS = [("4.1", "A feature", "does a thing", "Live", "Phase 1", "1.5-2 days",\n'
        '         "stands here", "None")]\n'
        'DATES = {"A feature": "2026-01-01"}\n' + data_extra)
    if sid:
        (demo / sync.ID_NAME).write_text(_json.dumps({"spreadsheetId": sid}))
    project = sync.Project(str(demo))
    project.active = project.resolve_initiative(None)
    return project


def _push(project, svc, *argv):
    """push() against a fake service. (outcome, printed text)."""
    import contextlib
    import io
    saved_service, saved_argv = sync.service, list(sys.argv)
    sync.service = lambda: svc
    sys.argv = [sys.argv[0], *argv]
    out = io.StringIO()
    try:
        with contextlib.redirect_stdout(out):
            outcome = sync.push(project)
    except SystemExit as e:
        outcome = f"exit: {e}"
    finally:
        sync.service, sys.argv = saved_service, saved_argv
    return outcome, out.getvalue()


def fix_round_checks():
    """Run the checks below; a crash is recorded as a FAIL naming the section it hit,
    so a missing feature reads as red rather than ending the run."""
    try:
        _fix_round_body()
    except Exception as e:  # noqa: BLE001 - the failure being guarded is a crash
        FAILS.append(f"fix-round checks crashed: {type(e).__name__}: {e}")
        print(f"  FAIL fix-round checks crashed: {type(e).__name__}: {e}")


def _fix_round_body():
    import stat
    import tempfile
    try:
        from googleapiclient.errors import HttpError
        from google.auth.exceptions import RefreshError
    except ImportError:
        print("\n  SKIP the fake-service checks: google-api-python-client is not installed")
        HttpError = RefreshError = None

    print("\n=== effort cells: ranges parse, unknown units fail the check ===")
    check("a range counts its lower end", sync.effort_days("1.5-2 days"), (1.5, True))
    check("'3 to 5 days' counts 3", sync.effort_days("3 to 5 days"), (3.0, True))
    check("hours are not days", sync.effort_days("2 hours"), (0.25, True))
    check("a week is five days", sync.effort_days("1 week"), (5.0, True))
    check("a session counts as a day", sync.effort_days("2 sessions"), (2.0, True))
    check("text that starts with no number is not counted, and is not an error",
          sync.effort_days("unknown"), (None, True))
    check("control: an unknown unit is an error", sync.effort_days("2 fortnights"),
          (None, False))
    report = FakeReport()
    sync.check_schema(FakeProject([row(effort="2 fortnights")]), report)
    check("check_schema fails an effort it cannot read",
          any("effort" in f for f in report.failures), True)
    report = FakeReport()
    sync.check_schema(FakeProject([row(effort="1.5-2 days")]), report)
    check("control: a range passes check_schema", report.failures, [])
    _, _, remaining, *_ = sync.summary_rows(
        FakeProject([row(status="Not started", effort="1.5-2 days")]))
    check("summary_rows reads a range instead of crashing", remaining, 1.5)

    print("\n=== PHASE_BUDGET is optional ===")
    shim = type("D", (), {"ROWS": [("1", "F", "w", "Live", "Phase 1", "1 day", "x", "None")],
                          "DATES": {"F": ""}})
    try:
        got = sync.default_sheet_rows(shim, "rows.py")[0][7]
    except AttributeError as e:
        got = f"AttributeError: {e}"
    check("a data module with no PHASE_BUDGET maps to a blank budget cell", got, "")

    print("\n=== the scaffold and the --repo message name no owner file ===")
    scaf = sync.SCAFFOLD.format(title="t")
    check("the scaffold's DATA_MODULE default is the neutral plan_status_rows.py",
          'DATA_MODULE = "plan_status_rows.py"' in scaf, True)
    check("it says PHASE_BUDGET is optional", "optional" in scaf.split("DATA_MODULE =")[0]
          and "PHASE_BUDGET" in scaf, True)
    with tempfile.TemporaryDirectory() as tmp:
        demo = Path(tmp) / "hand"
        demo.mkdir()
        (demo / sync.CONFIG_NAME).write_text('DATA_MODULE = "custom_rows.py"\n')
        saved = sync.PROJECTS
        sync.PROJECTS = Path(tmp)
        try:
            message = sync.hand_updated_message("/some/repo", "hand")
        finally:
            sync.PROJECTS = saved
    check("the --repo message names the config's own DATA_MODULE",
          "custom_rows.py" in message, True)
    check("control: it does not name a file the config never loads",
          "plan_status_rows.py" in message, False)

    print("\n=== PLAN_STATUS_PROJECTS moves the projects folder ===")
    saved_env = os.environ.get("PLAN_STATUS_PROJECTS")
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["PLAN_STATUS_PROJECTS"] = tmp
        try:
            again = importlib.util.module_from_spec(
                importlib.util.spec_from_file_location("sync2", HERE / "sync.py"))
            again.__spec__.loader.exec_module(again)
            got = again.PROJECTS
        finally:
            if saved_env is None:
                os.environ.pop("PLAN_STATUS_PROJECTS", None)
            else:
                os.environ["PLAN_STATUS_PROJECTS"] = saved_env
        check("the variable sets the folder --repo searches", got, Path(tmp))
    check("control: unset, it is the default folder",
          sync.PROJECTS if saved_env is None else Path.home() / ".claude" / "projects",
          Path.home() / ".claude" / "projects")

    print("\n=== the token check comes before the Google libraries ===")
    blocked = ("googleapiclient", "googleapiclient.discovery", "google.oauth2",
               "google.oauth2.credentials")
    saved_mods = {m: sys.modules.get(m, "absent") for m in blocked}
    saved_token = sync.TOKEN
    for m in blocked:
        sys.modules[m] = None
    sync.TOKEN = str(Path(tempfile.gettempdir()) / "no-such-plan-status-token.json")
    try:
        sync.service()
        outcome = "returned"
    except SystemExit as e:
        outcome = "token message" if "no Sheets token" in str(e) else f"exit: {e}"
    except ImportError:
        outcome = "ImportError"
    finally:
        sync.TOKEN = saved_token
        for m, v in saved_mods.items():
            if v == "absent":
                sys.modules.pop(m, None)
            else:
                sys.modules[m] = v
    check("a missing token says so even without the libraries", outcome, "token message")

    print("\n=== mint_token writes the token readable only by its owner ===")
    mspec = importlib.util.spec_from_file_location("mint_token", HERE / "mint_token.py")
    mint = importlib.util.module_from_spec(mspec)
    try:
        mspec.loader.exec_module(mint)
        writer = getattr(mint, "write_private", None)
    except ImportError as e:
        writer = None
        print(f"      (mint_token did not import: {type(e).__name__})")
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "token.json"
        old = os.umask(0)
        try:
            if writer:
                writer(str(target), "new")
                fresh = stat.S_IMODE(target.stat().st_mode)
                target.chmod(0o644)
                writer(str(target), "newer")
                replaced = (stat.S_IMODE(target.stat().st_mode), target.read_text())
            else:
                fresh, replaced = None, None
        finally:
            os.umask(old)
    check("a new token file is 0600 even under umask 0", fresh, 0o600)
    check("control: replacing a 0644 file leaves it 0600 with the new content",
          replaced, (0o600, "newer"))

    print("\n=== --check stays offline when SOURCES is declared ===")
    calls = []
    saved_run = sync._run
    with tempfile.TemporaryDirectory() as tmp:
        sync._run = lambda args, cwd=None: (calls.append(args[0]), (1, ""))[1]
        try:
            project = _demo_project(
                Path(tmp), data_extra='SOURCES = {"A feature": "feat/a"}\n',
                config_extra=f"REPO = {tmp!r}\n")
            import contextlib
            import io
            with contextlib.redirect_stdout(io.StringIO()):
                sync.do_check(project)
                offline = list(calls)
                sync.do_check(project, online=True)
        finally:
            sync._run = saved_run
    check("an offline check runs no git and no gh", offline, [])
    check("control: the online check does look them up", len(calls) > 0, True)

    if HttpError is None:
        return
    root_tmp = tempfile.TemporaryDirectory()
    root = Path(root_tmp.name)
    saved_projects = sync.PROJECTS
    sync.PROJECTS = root
    try:
        project = _demo_project(root)

        print("\n=== a wrong Sheet id is refused before anything is written ===")
        svc = FakeSvc(markers=["another-project"])
        outcome, _ = _push(project, svc)
        check("a Sheet marked as another project's is refused",
              "another-project" in str(outcome) and str(outcome).startswith("exit"), True)
        check("and nothing was written to it", svc.batches, [])
        svc = FakeSvc(markers=[project.name])
        outcome, _ = _push(project, svc)
        check("control: a Sheet marked as this project's is written", outcome, 0)
        svc = FakeSvc()
        outcome, printed = _push(project, svc)
        created = [r["createDeveloperMetadata"]["developerMetadata"]
                   for b in svc.batches for r in b["requests"]
                   if "createDeveloperMetadata" in r]
        check("an unmarked Sheet is written and marked as this project's",
              (outcome, [(m["metadataKey"], m["metadataValue"]) for m in created]),
              (0, [(sync.MARKER_KEY, project.name)]))
        svc = FakeSvc(markers=["another-project"])
        outcome, _ = _push(project, svc, "--adopt")
        claimed = [r for b in svc.batches for r in b["requests"]
                   if "deleteDeveloperMetadata" in r or "createDeveloperMetadata" in r]
        check("--adopt claims a Sheet marked as another project's",
              (outcome, len(claimed)), (0, 2))
        import json as _json
        other = root / "other-project"
        other.mkdir()
        (other / sync.ID_NAME).write_text(_json.dumps({"spreadsheetId": "SID_DEMO"}))
        svc = FakeSvc()
        outcome, _ = _push(project, svc)
        check("an id another local project also records is refused",
              ("other-project" in str(outcome), svc.batches), (True, []))
        check("and the refusal offers --adopt, not only a new Sheet",
              "--adopt" in str(outcome), True)
        svc = FakeSvc(markers=[project.name])
        outcome, printed = _push(project, svc)
        check("the real owner is written although another folder holds a copied id",
              (outcome, "other-project" in printed), (0, True))
        svc = FakeSvc(markers=["other-project"])
        outcome, _ = _push(project, svc)
        check("control: the copy holder is still refused by the owner mark",
              ("belongs to project 'other-project'" in str(outcome), svc.batches),
              (True, []))
        svc = FakeSvc()
        outcome, _ = _push(project, svc, "--adopt")
        check("--adopt marks an unmarked Sheet another folder also records",
              outcome, 0)
        (other / sync.ID_NAME).write_text(_json.dumps(
            {"initiatives": {"x": {"spreadsheetId": "SID_ELSE"}}}))
        svc = FakeSvc()
        outcome, _ = _push(project, svc)
        check("control: a different id in the other project is not a clash", outcome, 0)

        print("\n=== a failed column read is a refusal, not 'no strangers' ===")

        class Resp(dict):
            status, reason = 503, "busy"
        svc = FakeSvc(markers=[project.name], read_error=HttpError(Resp(), b"busy"))
        outcome, printed = _push(project, svc)
        check("the push refuses and rewrites nothing", (outcome, svc.wrote_cells()), (1, False))
        svc = FakeSvc(markers=[project.name], read_error=HttpError(Resp(), b"busy"))
        outcome, _ = _push(project, svc, "--force")
        check("control: --force goes ahead", (outcome, svc.wrote_cells()), (0, True))
        check("a tab name with an apostrophe is quoted by doubling it",
              sync.a1_tab("Bob's tab"), "'Bob''s tab'")
        quoted = _demo_project(root, name="quoted", sid="SID_Q",
                               config_extra='GRID_TAB = "Bob\'s tab"\n')
        svc = FakeSvc(markers=["quoted"], tabs=("Bob's tab", "Summary"))
        outcome, _ = _push(quoted, svc)
        check("the push reads and writes the quoted tab",
              (outcome, "'Bob''s tab'!A4:ZZ4" in svc.ranges), (0, True))

        print("\n=== an expired token says how to recover ===")
        svc = FakeSvc(meta_error=RefreshError("invalid_grant: Token has been expired"))
        outcome, _ = _push(project, svc)
        check("RefreshError becomes a message naming mint_token.py --force",
              "mint_token.py" in str(outcome) and "--force" in str(outcome), True)
        svc = FakeSvc(meta_error=ValueError("something else"))
        try:
            _push(project, svc)
            other_error = "swallowed"
        except ValueError:
            other_error = "raised"
        check("control: an unrelated error is not dressed up as an expired token",
              other_error, "raised")

        print("\n=== the read-back compares both tabs, and its control can fail ===")
        svc = FakeSvc(markers=[project.name])
        outcome, printed = _push(project, svc)
        check("an exact echo reads back clean", outcome, 0)
        merges = [r["mergeCells"]["range"]["startColumnIndex"]
                  for b in svc.batches for r in b["requests"] if "mergeCells" in r]
        check("every merge starts right of the two frozen columns",
              (len(merges) > 0, min(merges) >= 2), (True, True))
        svc = FakeSvc(markers=[project.name], corrupt=("Plan status", 4, 2))
        outcome, _ = _push(project, svc)
        check("a changed grid cell fails the read-back", outcome, 1)
        svc = FakeSvc(markers=[project.name], corrupt=("Summary", 1, 0))
        outcome, _ = _push(project, svc)
        check("a changed Summary cell fails the read-back", outcome, 1)
        saved_diff = sync.differing_cells
        sync.differing_cells = lambda *a, **k: []
        try:
            svc = FakeSvc(markers=[project.name], corrupt=("Plan status", 4, 2))
            outcome, printed = _push(project, svc)
        finally:
            sync.differing_cells = saved_diff
        check("control: a comparison that never sees a difference is caught",
              (outcome, "control did not fire" in printed), (1, True))
    finally:
        sync.PROJECTS = saved_projects
        root_tmp.cleanup()


def main():
    print("=== section numbers, including ranges and compound cells ===")
    check("a plain number", sync.covered_numbers(["7"]), {"7"})
    check("a sub-section also covers its parent",
          sync.covered_numbers(["7.2"]), {"7", "7.2"})
    check("a range expands", sync.covered_numbers(["4.1-4.3"]),
          {"4", "4.1", "4.2", "4.3"})
    check("a compound cell counts both",
          sync.covered_numbers(["9.2 / 9.8 B2"]), {"9", "9.2", "9.8", "2"})
    check("a word covers nothing", sync.covered_numbers(["new", "open"]), set())
    print("  control: a number NOT written down must be absent")
    check("control: 7.3 is not covered by 7.2", "7.3" in sync.covered_numbers(["7.2"]),
          False)

    print("\n=== plan coverage reports a real gap, and stays quiet on a covered plan ===")
    plan = HERE / "_test_plan.md"
    plan.write_text("# Title\n\n## 1. Background\n\n## 4. Model\n\n### 4.1 Document\n"
                    "\n### 4.2 Section\n\n## 9. Pipeline\n")
    try:
        full = FakeProject([row(section="1"), row(section="4.1-4.2"), row(section="9")],
                           plan=plan)
        report = FakeReport()
        sync.check_plan_coverage(full, report)
        check("a fully covered plan reports no gap",
              [line for line in report.lines if line.startswith("plan sections with no row")],
              ["plan sections with no row: 0"])

        print("  control: drop one row and the gap must appear")
        gapped = FakeProject([row(section="1"), row(section="9")], plan=plan)
        report = FakeReport()
        sync.check_plan_coverage(gapped, report)
        # Dropping the 4.1-4.2 row uncovers THREE headings, not two: the parent 4 as
        # well as its two children, because the plan numbers all three.
        check("control: the missing sections are named",
              [line for line in report.lines
               if line.startswith("plan sections with no row")],
              ["plan sections with no row: 3"])
        check("control: they are named individually, not just counted",
              sorted(l for l in report.lines if l.startswith("section ")),
              ["section 4.1: 4.1 Document", "section 4.2: 4.2 Section",
               "section 4: 4. Model"])

        print("  an excused section is not reported, and a stale excuse is flagged")
        excused = FakeProject([row(section="9")], plan=plan,
                              excused={"1": "background", "4": "x", "4.1": "x",
                                       "4.2": "x"})
        report = FakeReport()
        sync.check_plan_coverage(excused, report)
        check("excused sections stay quiet",
              [line for line in report.lines
               if line.startswith("plan sections with no row")],
              ["plan sections with no row: 0"])
        stale = FakeProject([row(section="9")], plan=plan, excused={"9": "no longer true"})
        report = FakeReport()
        sync.check_plan_coverage(stale, report)
        check("control: an excuse a row now covers is flagged",
              len([w for w in report.warnings if "excused" in w]), 1)
    finally:
        plan.unlink()

    print("\n=== dates ===")
    report = FakeReport()
    sync.check_dates(FakeProject([row(date="2026-01-01"), row(date="")]), report)
    check("a real past date and a blank both pass", report.failures, [])
    report = FakeReport()
    sync.check_dates(FakeProject([row(date="2099-01-01")]), report)
    check("control: a future date fails", len(report.failures), 1)
    check("control: the message says to read it from a record",
          "read from a commit" in report.failures[0].lower()
          or "READ from a commit" in report.failures[0], True)
    report = FakeReport()
    sync.check_dates(FakeProject([row(date="last tuesday")]), report)
    check("control: a date that is not a date fails", len(report.failures), 1)

    print("\n=== schema ===")
    report = FakeReport()
    sync.check_schema(FakeProject([row()]), report)
    check("a correct table passes", report.failures, [])
    report = FakeReport()
    bad = FakeProject([row()])
    bad.headers = list(sync.BASE_HEADERS)
    bad.headers[0], bad.headers[1] = bad.headers[1], bad.headers[0]
    sync.check_schema(bad, report)
    check("control: reordered headers fail", len(report.failures) >= 1, True)
    report = FakeReport()
    sync.check_schema(FakeProject([row(status="Nearly done")]), report)
    check("control: a status with no colour fails", len(report.failures), 1)
    report = FakeReport()
    short = FakeProject([row()[:8]])
    sync.check_schema(short, report)
    check("control: a short row fails", len(report.failures), 1)

    print("\n=== the request set protects the Sheet ===")
    grid = [[sync.cell("x")] for _ in range(5)]
    requests = sync.rewrite(1, grid, widths=[(0, 1, 96)], frozen_rows=4, frozen_cols=2,
                            merges=[(0, 1, 2, 10)], filter_range=(3, 5, 0, 10))
    kinds = [list(r)[0] for r in requests]
    check("no tab is ever deleted", any("deleteSheet" in k for k in kinds), False)
    check("no row height is ever set",
          any(r.get("updateDimensionProperties", {}).get("range", {})
              .get("dimension") == "ROWS" for r in requests), False)
    grid_steps = [r["updateSheetProperties"]["properties"]["gridProperties"]
                  for r in requests if "updateSheetProperties" in r]
    check("the freeze is cleared in its own request first",
          "rowCount" in grid_steps[0], False)
    check("then every row is dropped", grid_steps[1]["rowCount"], 1)
    check("then the grid is grown back", grid_steps[-1]["rowCount"], len(grid))
    check("the filter is cleared before anything else", kinds[0], "clearBasicFilter")

    def crossing(reqs, frozen):
        return [r for r in reqs if "mergeCells" in r
                and r["mergeCells"]["range"]["startColumnIndex"] < frozen
                < r["mergeCells"]["range"]["endColumnIndex"]]

    check("the banner merge stays inside the unfrozen block",
          len(crossing(requests, 2)), 0)
    bad_merge = sync.rewrite(1, grid, frozen_cols=2, merges=[(0, 1, 0, 10)])
    check("control: a full-width merge IS detected as crossing",
          len(crossing(bad_merge, 2)), 1)

    print("\n=== no module-level name is bound twice ===")
    names = collections.Counter()
    for node in ast.parse((HERE / "sync.py").read_text()).body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names[target.id] += 1
    check("nothing shadows an earlier constant",
          {n: c for n, c in names.items() if c > 1}, {})

    
    # ------------------------- dependencies, blockers, cross-references, the pin
    # Each is driven twice: on input it must reject, and on input it must pass over in
    # silence. A control proving only that a check CAN fire is half a control, and the
    # quiet half is what stops a noisy guard being switched off.

    def run(fn, project):
        report = FakeReport()
        fn(project, report)
        return report.failures, report.warnings

    def dep_row(feature, depends, section="1", status="Live"):
        return row(section=section, feature=feature, status=status, depends=depends)

    print("\n=== check_dependencies: warns, never fails ===")
    f, w = run(sync.check_dependencies, FakeProject([dep_row("A", ""), dep_row("B", "None.")]))
    check("an empty dependency warns", len(w), 1)
    check("it does NOT fail", len(f), 0)
    f, w = run(sync.check_dependencies, FakeProject([dep_row("A", "None. Ready.")]))
    check("a filled dependency is silent", (len(f), len(w)), (0, 0))

    print("\n=== check_blocker_measured: the mechanism, not one phrasing ===")
    f, _ = run(sync.check_blocker_measured, FakeProject([dep_row("A", "BLOCKED by a decision.")]))
    check("a BLOCKED cell with no measurement fails", len(f), 1)
    f, w = run(sync.check_blocker_measured,
               FakeProject([dep_row("A", "BLOCKED on the guard, measured 2026-08-28.")]))
    check("the live wording 'measured <date>' passes", (len(f), len(w)), (0, 0))
    f, _ = run(sync.check_blocker_measured,
               FakeProject([dep_row("A", "BLOCKED. Blocker last measured 2026-08-28: none.")]))
    check("the wording 'Blocker last measured <date>' also passes", len(f), 0)
    f, _ = run(sync.check_blocker_measured, FakeProject([dep_row("A", "BLOCKED, measured 2099-01-01.")]))
    check("a future measurement date fails", len(f), 1)
    f, w = run(sync.check_blocker_measured, FakeProject([dep_row("A", "None.")]))
    check("no BLOCKED rows: skipped, neither fails nor warns", (len(f), len(w)), (0, 0))

    print("\n=== check_cross_references: a dangling fix name is caught ===")
    pair = [dep_row("Search",
                    "BLOCKED, unblocked by 'Index builder'. measured 2026-08-28."),
            dep_row("Index builder", "Nothing external.", section="needed")]
    f, _ = run(sync.check_cross_references, FakeProject(pair))
    check("a fix name that exists resolves", len(f), 0)
    f, _ = run(sync.check_cross_references, FakeProject(
        [dep_row("S", "BLOCKED, unblocked by 'A row nobody wrote'. measured 2026-08-28.")]))
    check("a fix name that does not exist fails", len(f), 1)
    f, _ = run(sync.check_cross_references, FakeProject(
        [dep_row("S", "BLOCKED and that is all. measured 2026-08-28.")]))
    check("a BLOCKED cell naming no fix at all fails", len(f), 1)
    f, w = run(sync.check_cross_references, FakeProject([dep_row("A", "None.")]))
    check("no vocabulary in use: skipped, silent", (len(f), len(w)), (0, 0))

    print("\n=== check_pinned_control: the one check an empty rebuild cannot pass ===")
    pinned = FakeProject([dep_row("A", "None."), dep_row("B", "None.")])
    pinned.config.PINNED_CELL = ("A", 2, "does a thing")
    f, w = run(sync.check_pinned_control, pinned)
    check("a matching pin passes", (len(f), len(w)), (0, 0))
    pinned.config.PINNED_CELL = ("A", 2, "something else")
    f, _ = run(sync.check_pinned_control, pinned)
    check("a mismatched pin fails", len(f), 1)
    pinned.config.PINNED_CELL = ("A row since renamed", 2, "x")
    f, _ = run(sync.check_pinned_control, pinned)
    check("a pin aimed at a row that no longer exists fails", len(f), 1)
    empty = FakeProject([])
    empty.config.PINNED_CELL = ("A", 2, "does a thing")
    f, _ = run(sync.check_pinned_control, empty)
    check("a pin against an EMPTY rebuild fails, which is the whole point", len(f), 1)
    bare = FakeProject([dep_row("A", "None.")])
    f, w = run(sync.check_pinned_control, bare)
    check("no pin declared: warns rather than passing quietly", len(w), 1)

    print("\n=== for_initiative: one config value per initiative, the flat form untouched ===")

    class Named:
        def __init__(self, name):
            self.name = name

    multi = FakeProject([dep_row("A", "None.")])
    multi.initiatives = [Named("first"), Named("second")]
    multi.active = Named("second")
    multi.config.PINNED_CELL = {"first": ("A", 2, "does a thing"),
                                "second": ("A", 2, "something else")}
    f, _ = run(sync.check_pinned_control, multi)
    check("a per-initiative pin reads the ACTIVE initiative's tuple (second: mismatch)",
          len(f), 1)
    multi.active = Named("first")
    f, w = run(sync.check_pinned_control, multi)
    check("and the other tuple when that initiative is active (first: match)",
          (len(f), len(w)), (0, 0))
    multi.config.PINNED_CELL = ("A", 2, "does a thing")
    multi.active = Named("second")
    f, w = run(sync.check_pinned_control, multi)
    check("CONTROL: a flat tuple still applies to every initiative", (len(f), len(w)), (0, 0))
    multi.config.SECTIONS_WITHOUT_ROWS = {"1": "a reason", "4.2": "another"}
    check("a flat excuse map keyed by section number is NOT read as per-initiative",
          sync.for_initiative(multi, "SECTIONS_WITHOUT_ROWS", {}), {"1": "a reason", "4.2": "another"})
    multi.config.SECTIONS_WITHOUT_ROWS = {"first": {"1": "x"}, "second": {"9": "y"}}
    check("a per-initiative excuse map returns the active initiative's own",
          sync.for_initiative(multi, "SECTIONS_WITHOUT_ROWS", {}), {"9": "y"})
    multi.config.DOC_TITLE = {"first": "First: plan status", "second": "Second: plan status"}
    check("a per-initiative title follows the active initiative",
          sync.for_initiative(multi, "DOC_TITLE", "x"), "Second: plan status")
    multi.config.DOC_TITLE = "One title"
    check("a flat title is returned as it is", sync.for_initiative(multi, "DOC_TITLE", "x"),
          "One title")
    solo = FakeProject([dep_row("A", "None.")])
    solo.config.PINNED_CELL = {"default": ("A", 2, "does a thing")}
    f, w = run(sync.check_pinned_control, solo)
    check("a project with no declared initiatives reads the 'default' key",
          (len(f), len(w)), (0, 0))

    print("\n=== two initiatives on ONE Sheet: a tab pair each, or the push refuses ===")
    shared = FakeProject([dep_row("A", "None.")])
    shared.initiatives = [Named("default"), Named("webapp")]
    sheet_of = {"default": "SID1", "webapp": "SID1"}
    shared.spreadsheet_id = lambda i=None: sheet_of[(i or shared.active).name]
    shared.active = shared.initiatives[1]
    check("CONTROL: with no tab names declared, both use the default tabs",
          sync.tabs_for(shared), (sync.GRID_TAB, sync.SUMMARY_TAB))
    check("two initiatives on one Sheet with the SAME tabs is a clash",
          sync.shared_tab_clash(shared), "default")
    shared.config.GRID_TAB = {"default": "Plan status", "webapp": "Web app status"}
    shared.config.SUMMARY_TAB = {"default": "Summary", "webapp": "Web app summary"}
    check("per-initiative tab names follow the active initiative",
          sync.tabs_for(shared), ("Web app status", "Web app summary"))
    check("and give no clash", sync.shared_tab_clash(shared), None)
    check("the clash check leaves the active initiative as it found it",
          shared.active.name, "webapp")
    shared.config.SUMMARY_TAB = {"default": "Summary", "webapp": "Summary"}
    check("one shared tab of the pair is still a clash",
          sync.shared_tab_clash(shared), "default")
    shared.config.SUMMARY_TAB = "Summary"
    sheet_of["webapp"] = "SID2"
    check("CONTROL: the same tab names on DIFFERENT Sheets are no clash",
          sync.shared_tab_clash(shared), None)

    print("\n=== the double still mirrors the real Project ===")
    # The double must carry every attribute the real Project has. Assert the shape.
    # Ask an INSTANCE, not the class: config, data and headers are bound in __init__,
    # so a class-level dir() cannot see them and the check would fail on good input.
    needed = {"rows", "headers", "status_style", "config", "data"}
    fake = {n for n in dir(FakeProject([dep_row("A", "None.")])) if not n.startswith("_")}
    check("the double carries every attribute a check reads", needed - fake, set())
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        demo = Path(tmp) / "demo"
        demo.mkdir()
        (demo / sync.CONFIG_NAME).write_text('DATA_MODULE = "rows.py"\n')
        (demo / "rows.py").write_text("ROWS = []\nDATES = {}\nPHASE_BUDGET = {}\n")
        real = {n for n in dir(sync.Project(str(demo))) if not n.startswith("_")}
    check("control: the real Project has them too", needed - real, set())
    check("control: an attribute neither has is reported missing",
          {"a_name_nothing_defines"} - fake, {"a_name_nothing_defines"})

    print("\n=== spreadsheet_id honours the ACTIVE initiative ===")
    # With no argument it must look under the active initiative, the same key the
    # printed link uses.
    class FakeIds(sync.Project):
        def __init__(self, ids, active_name):
            self._ids_data = ids
            self.active = type("I", (), {"name": active_name})()
        def _ids(self):
            return self._ids_data
    named = {"initiatives": {"standardization": {"spreadsheetId": "SID_NAMED"}}}
    check("an id stored under a NAMED initiative is found",
          FakeIds(named, "standardization").spreadsheet_id(), "SID_NAMED")
    check("control: a different active name does not find it",
          FakeIds(named, "other").spreadsheet_id(), None)
    legacy = {"spreadsheetId": "SID_LEGACY"}
    check("the older flat file still resolves for 'default'",
          FakeIds(legacy, "default").spreadsheet_id(), "SID_LEGACY")
    check("control: a named initiative does not steal the legacy id",
          FakeIds(legacy, "standardization").spreadsheet_id(), None)

    # ------------------------------------------- regression checks, each reproduced first
    print("\n=== the scaffold matches the shape the skill actually expects ===")
    scaf = sync.SCAFFOLD.format(title="t")
    check("the scaffold does NOT define sheet_rows", "def sheet_rows" in scaf, False)
    check("it names DATES, which the default requires", "DATES" in scaf, True)
    check("it carries PINNED_CELL, the anti-vacuous control", "PINNED_CELL" in scaf, True)
    check("it carries REPO, which --repo resolves by", "REPO" in scaf, True)
    # Parse it rather than exec it. Running generated text buys nothing here: what this
    # asserts is that
    # the scaffold is valid Python defining exactly the expected names, and the syntax tree
    # answers both without running anything.
    tree = ast.parse(scaf)
    assigned = sorted({target.id for node in tree.body
                       if isinstance(node, ast.Assign)
                       for target in node.targets if isinstance(target, ast.Name)})
    check("the scaffold parses and assigns exactly the expected names", assigned,
          ["DATA_MODULE", "DOC_TITLE", "HAND_UPDATED_REPOS", "PINNED_CELL", "PLAN", "REPO",
           "SECTIONS_WITHOUT_ROWS"])
    check("control: it defines no functions at all",
          [n.name for n in tree.body if isinstance(n, ast.FunctionDef)], [])

    print("\n=== a failed lookup stays unknown, it never becomes an answer ===")
    check("no repo at all", sync.repo_facts(None, "x")["on_main"], "unknown")
    check("a path that is not a repository", sync.repo_facts("/", "x")["head"], "unknown")
    import subprocess
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(["git", "-C", tmp, "init", "-q", "-b", "main"], check=True)
        subprocess.run(["git", "-C", tmp, "-c", "user.email=t@t", "-c", "user.name=t",
                        "commit", "-q", "--allow-empty", "-m", "x"], check=True)
        check("control: a real repo and a real branch answers",
              sync.repo_facts(tmp, "main")["head"] not in ("unknown", "not found"), True)

    print("\n=== cross-references survive an apostrophe and a short name ===")
    def xr(rows):
        r = FakeReport()
        sync.check_cross_references(FakeProject(rows), r)
        return r.failures
    apos = [dep_row("A", "BLOCKED, unblocked by \"Tenant's audit trail\". measured 2026-09-06."),
            dep_row("Tenant's audit trail", "Nothing external.", section="needed")]
    check("an apostrophe inside the name resolves", len(xr(apos)), 0)
    short = [dep_row("A", "BLOCKED, unblocked by 'SSO'. measured 2026-09-06."),
             dep_row("SSO", "Nothing external.", section="needed")]
    check("a three-letter name resolves", len(xr(short)), 0)
    contraction = [dep_row("A", "BLOCKED; can't proceed until 'Retry policy'. measured 2026-09-06."),
                   dep_row("Retry policy", "Nothing external.", section="needed")]
    check("a contraction earlier in the sentence does not swallow it",
          len(xr(contraction)), 0)
    check("control: a name no row carries still FAILS",
          len(xr([dep_row("A", "BLOCKED, unblocked by 'Nothing here'. measured 2026-09-06.")])), 1)

    print("\n=== the measurement date is the one beside the measurement word ===")
    def bm(cell):
        r = FakeReport()
        sync.check_blocker_measured(FakeProject([dep_row("A", cell)]), r)
        return r.failures
    check("a future TARGET date beside a real measurement passes",
          len(bm("BLOCKED until 2099-01-01; measured 2026-09-06.")), 0)
    check("a negation does not pass on the word alone",
          len(bm("BLOCKED; not checked since 2026-08-28.")), 1)
    check("control: a genuine measurement still passes",
          len(bm("BLOCKED on the guard, measured 2026-08-28.")), 0)
    check("control: a FUTURE measurement date still fails",
          len(bm("BLOCKED, measured 2099-01-01.")), 1)
    # The adjacency rule: a "no longer" that negates another word must not count.
    for cell, want, label in (
            ("BLOCKED; not checked since 2026-08-28.", 1, "a real negation fails"),
            ("BLOCKED; never measured.", 1, "never measured fails"),
            ("BLOCKED; has not yet been measured.", 1, "two filler words still fails"),
            ("BLOCKED, THE OLD REASONS NO LONGER HOLD, measured 2026-08-28.", 0,
             "a negation of another word PASSES"),
            ("BLOCKED on the guard, measured 2026-08-28.", 0, "a plain measurement passes"),
    ):
        check(label, len(bm(cell)), want)

    # A Sheet can track packages built in a SECOND repository whose rows are updated by
    # hand. A release in that second repository must find the same Sheet.
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        projects = Path(tmp)
        main_repo, side_repo, other = (projects / n for n in ("repo_main", "repo_side", "repo_other"))
        for d in (main_repo, side_repo, other):
            d.mkdir()

        def config(name, body):
            (projects / name).mkdir(exist_ok=True)
            (projects / name / sync.CONFIG_NAME).write_text(body)

        saved = sync.PROJECTS
        sync.PROJECTS = projects
        try:
            config("Calc", f"REPO = {str(main_repo)!r}\n")
            check("control: without the declaration the second repo finds no Sheet",
                  sync.project_for_repo(str(side_repo)), None)
            config("Calc", f"REPO = {str(main_repo)!r}\n"
                           f"HAND_UPDATED_REPOS = ({str(side_repo)!r},)\n")
            check("the main repository still finds its Sheet",
                  sync.project_for_repo(str(main_repo)), "Calc")
            check("a declared hand-updated repository finds the same Sheet",
                  sync.project_for_repo(str(side_repo)), "Calc")
            check("the match says the rows are hand-updated",
                  sync.hand_updated(str(side_repo), "Calc"), True)
            check("control: the main repository's rows are not hand-updated",
                  sync.hand_updated(str(main_repo), "Calc"), False)
            check("an undeclared repository still finds nothing",
                  sync.project_for_repo(str(other)), None)
            config("Other", f"REPO = {str(other)!r}\n"
                            f"HAND_UPDATED_REPOS = ({str(side_repo)!r},)\n")
            try:
                sync.project_for_repo(str(side_repo))
                claimed = "no error"
            except SystemExit as e:
                claimed = "refused" if "2 projects claim" in str(e) else str(e)
            check("two Sheets claiming one repository are refused", claimed, "refused")
        finally:
            sync.PROJECTS = saved

    # A release run from a git WORKTREE of the declared repository must find the same
    # Sheet. The declared path and the worktree path differ; the repository is the same one.
    import subprocess
    with tempfile.TemporaryDirectory() as tmp:
        projects = Path(tmp)
        repo, unrelated = projects / "repo_main", projects / "repo_unrelated"
        repo.mkdir(); unrelated.mkdir()
        git = lambda *a: subprocess.run(["git", "-C", str(repo), *a], check=True,
                                        capture_output=True)
        git("init", "-q"); git("-c", "user.email=t@t", "-c", "user.name=t",
                               "commit", "-q", "--allow-empty", "-m", "x")
        wt = projects / "repo_wt"
        git("worktree", "add", "-q", "--detach", str(wt))
        sub = wt / "sub"
        sub.mkdir()
        (projects / "Calc").mkdir()
        (projects / "Calc" / sync.CONFIG_NAME).write_text(f"REPO = {str(repo)!r}\n")
        saved = sync.PROJECTS
        sync.PROJECTS = projects
        try:
            check("control: the declared repository finds its Sheet",
                  sync.project_for_repo(str(repo)), "Calc")
            check("a worktree of the declared repository finds the same Sheet",
                  sync.project_for_repo(str(wt)), "Calc")
            check("a subfolder of a worktree finds the same Sheet",
                  sync.project_for_repo(str(sub)), "Calc")
            check("control: an unrelated folder (not git) still finds nothing",
                  sync.project_for_repo(str(unrelated)), None)
        finally:
            sync.PROJECTS = saved

    print("\n=== a machine with no projects folder gets a message, not a traceback ===")
    saved = sync.PROJECTS
    with tempfile.TemporaryDirectory() as tmp:
        sync.PROJECTS = Path(tmp) / "no-such-folder"
        try:
            sync.project_dir("anything")
            outcome = "returned"
        except SystemExit as e:
            outcome = "message" if "does not exist" in str(e) else f"other exit: {e}"
        except Exception as e:  # noqa: BLE001 - the failure being guarded is a crash
            outcome = type(e).__name__
        finally:
            sync.PROJECTS = saved
    check("a missing projects folder exits with a message", outcome, "message")
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "demo-project").mkdir()
        sync.PROJECTS = Path(tmp)
        try:
            found = sync.project_dir("demo").name
        finally:
            sync.PROJECTS = saved
    check("control: an existing projects folder still resolves a fragment", found,
          "demo-project")

    print("\n=== merged pull requests every row omits ===")
    def wrow(feature, what):
        r = row(feature=feature)
        r[2] = what
        return r
    rows = [wrow("A", "Released as 99749b6 (PR #10), live."),
            wrow("B", "Fix shipped as 2a3f428 on 2026-10-20."),
            wrow("C", "Draft PR #31 open.")]
    merged = [{"number": 10, "mergeCommit": {"oid": "99749b6aaaa"}},
              {"number": 15, "mergeCommit": {"oid": "2a3f428bbbb"}},
              {"number": 3, "mergeCommit": {"oid": "0d6b0d3cccc"}},
              {"number": 7, "mergeCommit": {"oid": "99c8dd5dddd"}}]
    check("a PR named as 'PR #10' is recorded; one named only by its merge commit is too; "
          "'PR #31' does not cover #3",
          sync.unrecorded_prs(rows, merged, {}), [3, 7])
    check("control: a PR listed as needing no row, with its reason, is not reported",
          sync.unrecorded_prs(rows, merged, {3: "banner only", 7: "x"}), [])
    check("control: every PR recorded gives an empty list",
          sync.unrecorded_prs(rows + [wrow("D", "PR #3 and PR #7")], merged, {}), [])

    class Cfg:
        REPO = "/nowhere"
    proj = FakeProject(rows)
    proj.config = Cfg()
    rep = FakeReport()
    sync.check_released_prs(proj, rep, merged=merged)
    check("not switched on (no PRS_TRACKED_FROM): the count is shown, nothing fails",
          (len(rep.failures), any("merged PRs no row names: 2" in l for l in rep.lines)), (0, True))
    Cfg.PRS_TRACKED_FROM = 1
    rep = FakeReport()
    sync.check_released_prs(proj, rep, merged=merged)
    check("switched on: each unrecorded PR from PRS_TRACKED_FROM on is a failure",
          len(rep.failures), 2)
    Cfg.PRS_TRACKED_FROM = 5
    rep = FakeReport()
    sync.check_released_prs(proj, rep, merged=merged)
    check("switched on from #5: #3 is before tracking began, #7 still fails",
          [f for f in rep.failures if "#7" in f] != [] and not any("#3 " in f for f in rep.failures), True)
    rep = FakeReport()
    sync.check_released_prs(proj, rep, merged=None, lister=lambda repo: None)
    check("a lookup that could not answer warns and never fails (unknown is not absence)",
          (len(rep.failures), len(rep.warnings)), (0, 1))

    fix_round_checks()

    print()
    print(f"{len(FAILS)} FAILED" if FAILS else "ALL CHECKS PASSED")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
