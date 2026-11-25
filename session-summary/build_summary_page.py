#!/usr/bin/env python3
"""Build the session summary page (skill session-summary): one self-contained HTML file.

    python3 build_summary_page.py <summary.json> --out-dir <dir> [--open]

The model writes the CONTENT as JSON; this script owns the LAYOUT, so every close
produces the same page shape, and the clock, so the time in the header is read,
never typed. It prints the path of the page it wrote. Exit 2 means the JSON is
missing something the page needs; the message names every problem.

The page is built for a reader who takes things in by eye: a row of coloured
status tiles first, then where the session sits in the bigger plan, then a
timeline, decisions, issues, who does what, the next-step cards, and a grid of
what was saved. Field rules: SKILL.md. Example: reference/example.json.

Required: project, project_about, title, one_line, recommendation,
          done [{what, proof?}] (1+), next [{title, what, changes?, command?, pick?}] (1-3, one pick max),
          saved [{where, state?, detail?, path?, items?}] (1+)
Optional: status [{label, value, tone}], scope [{name, state}], decisions [{choice, recorded?}],
          issues [{what, effect?}], yours [str], mine [str], pages [{title, path}], cleaned [str]

Text may hold `backticks` for code. Hebrew is fine: every text block carries
dir="auto", so a right-to-left line aligns right by itself.
"""
import argparse
import datetime as dt
import html
import json
import os
import pathlib
import re
import sys
import webbrowser
from urllib.parse import quote

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None

# Time zone for the header. SESSION_SUMMARY_TZ is an IANA name ("Europe/London");
# empty means this computer's own zone. SESSION_SUMMARY_TZ_LABEL names it on the page.
LOCAL_ZONE = os.environ.get("SESSION_SUMMARY_TZ", "")
LOCAL_LABEL = os.environ.get("SESSION_SUMMARY_TZ_LABEL", "local time")

REQUIRED_STR = ("project", "project_about", "title", "one_line", "recommendation")
TONES = ("good", "warn", "bad", "info")
SCOPE_STATES = ("done", "now", "next", "later")
SAVE_STATES = {  # state -> (chip text, tone)
    "updated": ("updated", "good"),
    "pushed": ("pushed", "good"),
    "unchanged": ("no change", "info"),
    "uncommitted": ("not committed", "warn"),
    "refused": ("refused", "bad"),
    "skipped": ("skipped", "info"),
    "not-due": ("not due", "info"),
}


class SummaryError(ValueError):
    pass


def _need_list(d, k, probs, min_len=0):
    v = d.get(k)
    if v is None:
        if min_len:
            probs.append(f"'{k}' is required")
        return []
    if not isinstance(v, list):
        probs.append(f"'{k}' must be a list")
        return []
    if len(v) < min_len:
        probs.append(f"'{k}' needs at least {min_len} item(s)")
    return v


def _objs(items, k, field, probs):
    for i, it in enumerate(items):
        if not isinstance(it, dict) or not str(it.get(field, "")).strip():
            probs.append(f"{k}[{i}] needs '{field}'")


def validate(d):
    """Raise SummaryError naming every problem, so one run fixes them all."""
    if not isinstance(d, dict):
        raise SummaryError("top level must be a JSON object")
    probs = []
    for k in REQUIRED_STR:
        if not isinstance(d.get(k), str) or not d[k].strip():
            probs.append(f"'{k}' must be a non-empty string")
    _objs(_need_list(d, "done", probs, 1), "done", "what", probs)
    _objs(_need_list(d, "issues", probs), "issues", "what", probs)
    _objs(_need_list(d, "decisions", probs), "decisions", "choice", probs)
    _objs(_need_list(d, "pages", probs), "pages", "path", probs)
    for k in ("yours", "mine", "cleaned"):
        _need_list(d, k, probs)
    for i, it in enumerate(_need_list(d, "status", probs)):
        if not isinstance(it, dict) or not it.get("label") or not it.get("value"):
            probs.append(f"status[{i}] needs 'label' and 'value'")
        elif it.get("tone", "info") not in TONES:
            probs.append(f"status[{i}] tone must be one of {', '.join(TONES)}")
    scope = _need_list(d, "scope", probs)
    for i, it in enumerate(scope):
        if not isinstance(it, dict) or not it.get("name"):
            probs.append(f"scope[{i}] needs 'name'")
        elif it.get("state") not in SCOPE_STATES:
            probs.append(f"scope[{i}] state must be one of {', '.join(SCOPE_STATES)}")
    if scope and not any(isinstance(it, dict) and it.get("state") == "now" for it in scope):
        probs.append("'scope' has no 'now' step, so the reader cannot see where this session sits")
    saved = _need_list(d, "saved", probs, 1)
    _objs(saved, "saved", "where", probs)
    for i, it in enumerate(saved):
        if isinstance(it, dict) and it.get("state") and it["state"] not in SAVE_STATES:
            probs.append(f"saved[{i}] state must be one of {', '.join(SAVE_STATES)}")
    nxt = d.get("next")
    if not isinstance(nxt, list) or not 1 <= len(nxt) <= 3:
        probs.append("'next' needs 1 to 3 options (the next move is always the user's)")
    else:
        _objs(nxt, "next", "title", probs)
        _objs(nxt, "next", "what", probs)
        if sum(bool(isinstance(it, dict) and it.get("pick")) for it in nxt) > 1:
            probs.append("'next' marks more than one pick")
    if probs:
        raise SummaryError("; ".join(probs))


def _t(s):
    """Escape text, then turn `x` into <code>x</code>."""
    s = html.escape(str(s), quote=True)
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", s)


def stamp(now_utc=None):
    """('<date>, <HH:MM> <label> (<HH:MM> UTC)', '<date>_<HHMM>'), read from the clock."""
    now_utc = now_utc or dt.datetime.now(dt.timezone.utc)
    try:
        local = now_utc.astimezone(ZoneInfo(LOCAL_ZONE)) if (ZoneInfo and LOCAL_ZONE) else now_utc.astimezone()
    except Exception:  # a zone name this Python cannot load (Windows without tzdata)
        local = now_utc.astimezone()
    return (f"{local:%Y-%m-%d, %H:%M} {LOCAL_LABEL} ({now_utc:%H:%M} UTC)",
            f"{local:%Y-%m-%d_%H%M}")


CSS = """
:root{--accent:#1d2a44;--bg:#f4f6f9;--fg:#1d2430;--card:#fff;--line:#dde2ea;--muted:#5b6575;--band:#1d2a44;--code:#eef1f5;
--good:#2f7d4f;--goodbg:#eaf6ef;--warn:#a5531a;--warnbg:#fdf3ea;--bad:#b3261e;--badbg:#fdecea;--info:#3b5b8c;--infobg:#ebf1fa}
@media (prefers-color-scheme:dark){:root{--accent:#3d64a8;--bg:#12161d;--fg:#e4e8ef;--card:#1b212b;--line:#2e3644;--muted:#9aa4b4;--band:#0c1220;--code:#262e3b;
--good:#5fbf86;--goodbg:#17281e;--warn:#e39a62;--warnbg:#2a1f16;--bad:#f08a80;--badbg:#2c1715;--info:#8fb0e3;--infobg:#172131}}
*{box-sizing:border-box}body{font:16px/1.55 -apple-system,"Segoe UI",Arial,sans-serif;margin:0;background:var(--bg);color:var(--fg)}
.band{background:var(--band);color:#fff;padding:14px 28px}.band b{font-size:17px}.band small{display:block;opacity:.8}
main{max-width:1000px;margin:0 auto;padding:22px 28px 60px}
h1{font-size:25px;margin:6px 0 10px}h2{font-size:19px;margin:34px 0 12px;display:flex;align-items:center;gap:10px}
h2 .n{display:inline-grid;place-items:center;width:28px;height:28px;border-radius:50%;background:var(--accent);color:#fff;font-size:14px}
.lead{font-size:18px;background:var(--card);border:1px solid var(--line);border-left:6px solid var(--good);border-radius:10px;padding:14px 18px}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin:16px 0 4px}
.tile{border-radius:12px;padding:12px 14px;border:1px solid var(--line);border-top:5px solid var(--c);background:var(--card)}
.tile .l{font-size:13px;text-transform:uppercase;letter-spacing:.04em;color:var(--muted)}
.tile .v{font-size:17px;font-weight:600;margin-top:2px;color:var(--c)}
.t-good{--c:var(--good)}.t-warn{--c:var(--warn)}.t-bad{--c:var(--bad)}.t-info{--c:var(--info)}
.scope{display:flex;flex-wrap:wrap;gap:4px;margin:4px 0}
.step{position:relative;padding:10px 22px 10px 26px;font-size:14px;background:var(--card);border:1px solid var(--line);
clip-path:polygon(0 0,calc(100% - 14px) 0,100% 50%,calc(100% - 14px) 100%,0 100%,14px 50%);flex:1 1 140px;min-height:62px}
.step:first-child{clip-path:polygon(0 0,calc(100% - 14px) 0,100% 50%,calc(100% - 14px) 100%,0 100%);padding-left:14px}
.step small{display:block;font-size:11px;text-transform:uppercase;letter-spacing:.05em;color:var(--muted)}
.s-done{background:var(--goodbg)}.s-done small{color:var(--good)}
.s-now{background:var(--accent);color:#fff;font-weight:600}.s-now small{color:#c9d6f0}
.s-next{background:var(--warnbg)}.s-next small{color:var(--warn)}
.tl{list-style:none;margin:0;padding:0 0 0 8px;border-left:3px solid var(--line)}
.tl li{position:relative;margin:0 0 14px;padding:0 0 0 22px}
.tl li::before{content:"";position:absolute;left:-10px;top:5px;width:15px;height:15px;border-radius:50%;background:var(--good);border:3px solid var(--bg)}
.proof{display:block;color:var(--muted);font-size:14px}
.box{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 18px}
.grid2{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:12px}
.dec{background:var(--infobg);border:1px solid var(--line);border-left:5px solid var(--info);border-radius:10px;padding:10px 14px}
.issue{background:var(--warnbg);border:1px solid var(--line);border-left:5px solid var(--warn);border-radius:10px;padding:10px 16px;margin:8px 0}
.who h3{margin:0 0 8px;font-size:16px;display:flex;gap:8px;align-items:center}
.who.you{border-top:5px solid var(--warn)}.who.me{border-top:5px solid var(--info)}
ul{margin:0;padding-left:22px}li{margin:6px 0}
.cards{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 14px}
.card.pick{border:2px solid var(--good);background:var(--goodbg)}
.tag{display:inline-block;background:var(--good);color:#fff;font-size:12px;border-radius:4px;padding:1px 6px;margin-bottom:6px}
.card p{margin:6px 0}.lbl{color:var(--muted);font-size:13px}
.saved{display:grid;grid-template-columns:repeat(auto-fit,minmax(290px,1fr));gap:12px}
.sv{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 14px}
.sv .top{display:flex;justify-content:space-between;gap:8px;align-items:baseline}
.chip{font-size:12px;font-weight:600;border-radius:999px;padding:2px 9px;white-space:nowrap;color:var(--c);background:var(--cb)}
.c-good{--c:var(--good);--cb:var(--goodbg)}.c-warn{--c:var(--warn);--cb:var(--warnbg)}.c-bad{--c:var(--bad);--cb:var(--badbg)}.c-info{--c:var(--info);--cb:var(--infobg)}
.sv p{margin:6px 0 0}.sv ul{font-size:14px;margin-top:4px}
code{background:var(--code);padding:1px 5px;border-radius:4px;font-size:.9em;overflow-wrap:anywhere}
a{color:var(--info)}.empty{color:var(--muted)}
"""


def _list(items, empty):
    if not items:
        return f'<p class="empty">{_t(empty)}</p>'
    return "<ul>" + "".join(f'<li dir="auto">{_t(x)}</li>' for x in items) + "</ul>"


class _Sections:
    """Numbers the h2 headings in the order they are actually emitted."""

    def __init__(self):
        self.n = 0

    def __call__(self, title):
        self.n += 1
        return f'<h2><span class="n">{self.n}</span>{_t(title)}</h2>'


def render(d, now_utc=None):
    validate(d)
    when, _ = stamp(now_utc)
    h = _Sections()
    o = ['<!doctype html><html lang="en"><head><meta charset="utf-8">'
         '<meta name="viewport" content="width=device-width,initial-scale=1">'
         f"<title>Session summary: {_t(d['project'])}</title><style>{CSS}</style></head><body>",
         f'<div class="band"><b>Project: {_t(d["project"])}</b> ({_t(d["project_about"])})'
         f"<small>Session summary, closed {_t(when)}</small></div><main>",
         f'<h1 dir="auto">{_t(d["title"])}</h1>',
         f'<div class="lead" dir="auto">{_t(d["one_line"])}</div>']

    if d.get("status"):
        o.append('<div class="tiles">')
        for it in d["status"]:
            o.append(f'<div class="tile t-{it.get("tone", "info")}"><div class="l">{_t(it["label"])}</div>'
                     f'<div class="v" dir="auto">{_t(it["value"])}</div></div>')
        o.append("</div>")

    if d.get("scope"):
        o.append(h("Where this session sits") + '<div class="scope">')
        label = {"done": "done", "now": "this session", "next": "next", "later": "later"}
        for it in d["scope"]:
            st = it["state"]
            o.append(f'<div class="step s-{st}" dir="auto"><small>{label[st]}</small>{_t(it["name"])}</div>')
        o.append("</div>")

    o.append(h("What we did") + '<div class="box"><ol class="tl">')
    for it in d["done"]:
        proof = f'<span class="proof">{_t(it["proof"])}</span>' if it.get("proof") else ""
        o.append(f'<li dir="auto">{_t(it["what"])}{proof}</li>')
    o.append("</ol></div>")

    if d.get("decisions"):
        o.append(h("Decisions you made") + '<div class="grid2">')
        for it in d["decisions"]:
            rec = f'<span class="proof">Recorded in {_t(it["recorded"])}</span>' if it.get("recorded") else ""
            o.append(f'<div class="dec" dir="auto">{_t(it["choice"])}{rec}</div>')
        o.append("</div>")

    o.append(h("Issues and blockers"))
    if not d.get("issues"):
        o.append('<p class="empty">No open issues, no blockers.</p>')
    for it in d.get("issues") or []:
        eff = f'<span class="proof">{_t(it["effect"])}</span>' if it.get("effect") else ""
        o.append(f'<div class="issue" dir="auto">{_t(it["what"])}{eff}</div>')

    o.append(h("Who does what") + '<div class="grid2">'
             f'<div class="box who you"><h3>Yours</h3>{_list(d.get("yours"), "Nothing waits on you.")}</div>'
             f'<div class="box who me"><h3>Mine, next session</h3>{_list(d.get("mine"), "Nothing queued for me.")}</div>'
             "</div>")

    o.append(h("Next step: your pick") + '<div class="cards">')
    for it in d["next"]:
        pick = bool(it.get("pick"))
        p = [f'<div class="card{" pick" if pick else ""}" dir="auto">']
        if pick:
            p.append('<span class="tag">My pick</span><br>')
        p.append(f"<b>{_t(it['title'])}</b><p>{_t(it['what'])}</p>")
        if it.get("changes"):
            p.append(f'<p><span class="lbl">What changes:</span> {_t(it["changes"])}</p>')
        if it.get("command"):
            p.append(f'<p><span class="lbl">Start with:</span> <code>{html.escape(str(it["command"]))}</code></p>')
        o.append("".join(p) + "</div>")
    o.append(f'</div><div class="box" style="margin-top:12px" dir="auto"><b>My recommendation:</b> {_t(d["recommendation"])}</div>')

    o.append(h("What was saved") + '<div class="saved">')
    for it in d["saved"]:
        chip = ""
        if it.get("state"):
            txt, tone = SAVE_STATES[it["state"]]
            chip = f'<span class="chip c-{tone}">{txt}</span>'
        p = [f'<div class="sv" dir="auto"><div class="top"><b>{_t(it["where"])}</b>{chip}</div>']
        if it.get("detail"):
            p.append(f"<p>{_t(it['detail'])}</p>")
        if it.get("items"):
            p.append(_list(it["items"], ""))
        if it.get("path"):
            p.append(f'<p><code>{html.escape(str(it["path"]))}</code></p>')
        o.append("".join(p) + "</div>")
    o.append("</div>")

    if d.get("pages"):
        o.append(h("Pages from this session") + '<div class="box"><ul>')
        for it in d["pages"]:
            href = "file://" + quote(str(it["path"]))
            title = _t(it.get("title") or os.path.basename(str(it["path"])))
            o.append(f'<li dir="auto"><a href="{html.escape(href)}">{title}</a><span class="proof">'
                     f'<code>{html.escape(str(it["path"]))}</code></span></li>')
        o.append("</ul></div>")

    if d.get("cleaned"):
        o.append(h("Close housekeeping") + f'<div class="box">{_list(d["cleaned"], "")}</div>')
    o.append("</main></body></html>\n")
    return "".join(o)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("json_path")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--open", action="store_true", help="open the page in the default browser")
    a = ap.parse_args(argv)
    try:
        with open(a.json_path, encoding="utf-8") as f:
            d = json.load(f)
        page = render(d)
    except (OSError, json.JSONDecodeError, SummaryError) as e:
        print(f"summary page NOT built: {e}", file=sys.stderr)
        return 2
    _, slug = stamp()
    os.makedirs(a.out_dir, exist_ok=True)
    path = os.path.join(a.out_dir, f"session_summary_{slug}.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(page)
    print(path)
    if a.open:
        webbrowser.open(pathlib.Path(path).resolve().as_uri())  # Mac, Windows and Linux
    return 0


if __name__ == "__main__":
    sys.exit(main())
