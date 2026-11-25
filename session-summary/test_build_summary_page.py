#!/usr/bin/env python3
"""Tests for build_summary_page. Run: python3 test_build_summary_page.py

Each test checks a contrast: what must appear AND what must not, so a renderer
that prints everything, or a validator that accepts everything, goes red.
"""
import copy
import datetime as dt
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_summary_page as b  # noqa: E402

GOOD = {
    "project": "demo_project",
    "project_about": "an invented project for tests",
    "title": "Release 3 shipped",
    "one_line": "Release 3 is live. Next is the run with documents.",
    "done": [{"what": "Released release 3", "proof": "commit `1a2b3c4`"}],
    "issues": [{"what": "Events land on the wrong page", "effect": "A reader sees them on the wrong page"}],
    "yours": ["Answer the two open questions"],
    "mine": ["Diagnose where the new events land"],
    "next": [
        {"title": "Ask for a new run", "what": "Run it with documents", "changes": "Tests fix 3",
         "command": "cd ~/x && claude", "pick": True},
        {"title": "Answer the questions first", "what": "Two short calls"},
    ],
    "recommendation": "Ask for the run first.",
    "saved": [{"where": "TODO", "path": "/tmp/TODO.md"}],
    "cleaned": ["Stopped the dev server on :8002"],
    "status": [{"label": "Shipped", "value": "1a2b3c4", "tone": "good"},
               {"label": "Waiting on you", "value": "2 items", "tone": "warn"}],
    "scope": [{"name": "Run 5", "state": "done"}, {"name": "Release 3", "state": "now"},
              {"name": "Run with documents", "state": "next"}],
    "decisions": [{"choice": "Skip the deck slides", "recorded": "CLAUDE_DECISIONS.md"}],
    "pages": [{"title": "Hook page", "path": "/tmp/a b.html"}],
}
NOW = dt.datetime(2026, 11, 25, 7, 33, tzinfo=dt.timezone.utc)


class RenderTests(unittest.TestCase):
    def test_all_sections_in_order(self):
        page = b.render(GOOD, NOW)
        heads = ["Where this session sits", "What we did", "Decisions you made", "Issues and blockers",
                 "Who does what", "Next step: your pick", "What was saved", "Pages from this session",
                 "Close housekeeping"]
        pos = [page.index("</span>" + h + "</h2>") for h in heads]
        self.assertEqual(pos, sorted(pos))
        self.assertIn('<span class="n">9</span>Close housekeeping', page)

    def test_header_time_is_read_with_both_zones(self):
        try:
            b.ZoneInfo("Europe/Paris")
        except Exception:
            self.skipTest("this Python has no time-zone data (Windows without tzdata)")
        old = (b.LOCAL_ZONE, b.LOCAL_LABEL)
        b.LOCAL_ZONE, b.LOCAL_LABEL = "Europe/Paris", "Paris time"
        try:
            page = b.render(GOOD, NOW)
        finally:
            b.LOCAL_ZONE, b.LOCAL_LABEL = old
        self.assertIn("2026-11-25, 08:33 Paris time (07:33 UTC)", page)  # winter is UTC+1
        self.assertIn("Project: demo_project", page)

    def test_empty_zone_uses_this_computers_zone(self):
        old = (b.LOCAL_ZONE, b.LOCAL_LABEL)
        b.LOCAL_ZONE, b.LOCAL_LABEL = "", "local time"
        try:
            page = b.render(GOOD, NOW)
        finally:
            b.LOCAL_ZONE, b.LOCAL_LABEL = old
        local = NOW.astimezone()
        self.assertIn(f"{local:%Y-%m-%d, %H:%M} local time (07:33 UTC)", page)

    def test_exactly_the_picked_card_is_marked(self):
        page = b.render(GOOD, NOW)
        self.assertEqual(page.count("My pick</span>"), 1)
        self.assertEqual(page.count('class="card pick"'), 1)
        self.assertLess(page.index("My pick"), page.index("Answer the questions first"))

    def test_text_is_escaped_and_backticks_become_code(self):
        d = copy.deepcopy(GOOD)
        d["one_line"] = "<script>alert(1)</script> see `x.py`"
        page = b.render(d, NOW)
        self.assertNotIn("<script>alert", page)
        self.assertIn("&lt;script&gt;", page)
        self.assertIn("<code>x.py</code>", page)

    def test_hebrew_blocks_carry_dir_auto(self):
        d = copy.deepcopy(GOOD)
        d["one_line"] = "שלום עולם"
        page = b.render(d, NOW)
        self.assertIn('<div class="lead" dir="auto">שלום עולם</div>', page)

    def test_unknown_zone_falls_back_to_this_computers_zone(self):
        old = (b.LOCAL_ZONE, b.LOCAL_LABEL)
        b.LOCAL_ZONE, b.LOCAL_LABEL = "Not/A_Zone", "local time"
        try:
            page = b.render(GOOD, NOW)
        finally:
            b.LOCAL_ZONE, b.LOCAL_LABEL = old
        self.assertIn(f"{NOW.astimezone():%Y-%m-%d, %H:%M} local time (07:33 UTC)", page)

    def test_empty_lists_say_so_and_cleanup_section_drops(self):
        d = copy.deepcopy(GOOD)
        d["issues"], d["yours"], d["mine"], d["cleaned"] = [], [], [], []
        page = b.render(d, NOW)
        self.assertIn("No open issues, no blockers.", page)
        self.assertIn("Nothing waits on you.", page)
        self.assertNotIn("Close housekeeping", page)
        for k in ("status", "scope", "decisions", "pages"):
            d.pop(k)
        page = b.render(d, NOW)
        self.assertNotIn('class="tiles"', page)
        self.assertNotIn("Where this session sits", page)
        self.assertNotIn("Decisions you made", page)
        self.assertIn('<span class="n">1</span>What we did', page)


class VisualTests(unittest.TestCase):
    def test_status_tiles_carry_their_tone(self):
        page = b.render(GOOD, NOW)
        self.assertIn('<div class="tile t-good"><div class="l">Shipped</div>', page)
        self.assertIn('<div class="tile t-warn"><div class="l">Waiting on you</div>', page)

    def test_scope_marks_this_session(self):
        page = b.render(GOOD, NOW)
        self.assertEqual(page.count('class="step s-now"'), 1)
        self.assertIn('<small>this session</small>Release 3', page)
        self.assertIn('<small>done</small>Run 5', page)

    def test_saved_state_becomes_coloured_chip(self):
        d = copy.deepcopy(GOOD)
        d["saved"] = [{"where": "Board", "state": "refused"}, {"where": "Memory", "state": "pushed"},
                      {"where": "Plain"}]
        page = b.render(d, NOW)
        self.assertIn('<span class="chip c-bad">refused</span>', page)
        self.assertIn('<span class="chip c-good">pushed</span>', page)
        self.assertEqual(page.count('class="chip '), 2)

    def test_decision_shows_where_recorded(self):
        page = b.render(GOOD, NOW)
        self.assertIn("Skip the deck slides<span class=\"proof\">Recorded in CLAUDE_DECISIONS.md</span>", page)

    def test_pages_are_clickable_file_links(self):
        page = b.render(GOOD, NOW)
        self.assertIn('<a href="file:///tmp/a%20b.html">Hook page</a>', page)

    def test_example_json_renders(self):
        with open(os.path.join(HERE, "reference", "example.json"), encoding="utf-8") as f:
            b.render(json.load(f), NOW)


class ValidateTests(unittest.TestCase):
    def bad(self, mutate, needle):
        d = copy.deepcopy(GOOD)
        mutate(d)
        with self.assertRaises(b.SummaryError) as cm:
            b.render(d, NOW)
        self.assertIn(needle, str(cm.exception))

    def test_good_passes(self):
        b.validate(copy.deepcopy(GOOD))

    def test_no_next_steps_refused(self):
        self.bad(lambda d: d.update(next=[]), "'next' needs 1 to 3")

    def test_four_next_steps_refused(self):
        self.bad(lambda d: d.update(next=[{"title": "a", "what": "b"}] * 4), "'next' needs 1 to 3")

    def test_two_picks_refused(self):
        self.bad(lambda d: d.update(next=[{"title": "a", "what": "b", "pick": True}] * 2), "more than one pick")

    def test_missing_done_refused(self):
        self.bad(lambda d: d.pop("done"), "'done' is required")

    def test_missing_one_line_refused(self):
        self.bad(lambda d: d.update(one_line=" "), "'one_line'")

    def test_bad_tone_refused(self):
        self.bad(lambda d: d["status"].append({"label": "x", "value": "y", "tone": "pink"}), "tone must be")

    def test_scope_without_now_refused(self):
        self.bad(lambda d: d.update(scope=[{"name": "a", "state": "done"}]), "no 'now' step")

    def test_bad_scope_state_refused(self):
        self.bad(lambda d: d["scope"].append({"name": "a", "state": "soon"}), "state must be")

    def test_bad_saved_state_refused(self):
        self.bad(lambda d: d.update(saved=[{"where": "x", "state": "done-ish"}]), "saved[0] state")

    def test_missing_saved_refused(self):
        self.bad(lambda d: d.update(saved=[]), "'saved' needs")


class CliTests(unittest.TestCase):
    def test_writes_page_and_prints_path(self):
        with tempfile.TemporaryDirectory() as td:
            jp = os.path.join(td, "s.json")
            with open(jp, "w", encoding="utf-8") as f:
                json.dump(GOOD, f)
            out = io.StringIO()
            with redirect_stdout(out):
                rc = b.main([jp, "--out-dir", os.path.join(td, "pages")])
            self.assertEqual(rc, 0)
            path = out.getvalue().strip()
            self.assertTrue(os.path.basename(path).startswith("session_summary_"))
            with open(path, encoding="utf-8") as f:
                self.assertIn("Release 3 shipped", f.read())

    def test_bad_json_exits_2_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as td:
            jp = os.path.join(td, "s.json")
            with open(jp, "w", encoding="utf-8") as f:
                json.dump({"project": "x"}, f)
            err = io.StringIO()
            with redirect_stderr(err):
                rc = b.main([jp, "--out-dir", os.path.join(td, "pages")])
            self.assertEqual(rc, 2)
            self.assertIn("NOT built", err.getvalue())
            self.assertFalse(os.path.exists(os.path.join(td, "pages")))


if __name__ == "__main__":
    unittest.main(verbosity=1)
