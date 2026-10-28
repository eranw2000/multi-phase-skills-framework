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

    print()
    print(f"{len(FAILS)} FAILED" if FAILS else "ALL CHECKS PASSED")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
