---
model: opus
name: session-summary
description: Build one visual HTML page that sums up a work session, so the reader sees the whole scope at a glance - coloured status tiles (shipped, running, blockers, waiting on you), where the session sits in the bigger plan, a timeline of what was done with its proof, the decisions made, issues and blockers, who does what next, next-step cards with the pick marked, a tile per place the save touched with a state chip, and links to the pages the session wrote. Light and dark. The model writes the content as JSON; a bundled script owns the layout and reads the clock. /close-session runs it as its summary step. Use on its own when the user says "summarize this session", "visual summary", "recap as a page", "show me what we did", "session summary page", or "where do we stand, as a page". Not for a question to the user (that is an explainer page) and not for a manager-facing status page.
disable-model-invocation: false
---

# Session summary: one visual page for a session

One page tells the user, in plain words, what this session did, what is wrong or weak, who does what next, and which next step to take. The chat keeps its short lines; the page holds the detail.

**You write the content, the script writes the page.** Never hand-write the HTML: `build_summary_page.py` owns the layout (so every page looks the same), escapes the text, and reads the clock itself (so the time is never typed).

## Two ways it runs

- **Called by `/close-session`** (its summary step): run after the save and the cleanup, so `saved` and `cleaned` describe what really happened. The next steps come from the pin save-context just wrote, so the two never disagree.
- **On its own**, mid-session: same steps. Leave `cleaned` empty, and fill `saved` only with what was really written this session (a commit, a TODO edit, a deliverable). Nothing is saved by this skill itself.

## 1. Fill the JSON from the record, not from memory

Write it to the job's tmp dir (it is disposable; the page is the keeper). Every fact comes from the session's transcript and from commands run in it, never from recollection: a commit SHA from `git log`, a count from the command that produced it. Worked example (an invented project): `reference/example.json`.

| Field | What goes in |
|---|---|
| `project`, `project_about` | The project folder name, and a few words on what it is, so a reader who works several projects knows which one at a glance. |
| `title` | What the session was about, in a few words. |
| `one_line` | The state now and the next move, in one or two short sentences. If the user reads nothing else, this is enough. |
| `status` | 3 to 5 tiles, the first thing the eye lands on: `label`, `value`, `tone` (`good`, `warn`, `bad`, `info`). Use the same four every time where they fit: Shipped (or "Nothing shipped"), Running now, Blockers, Waiting on you (a count). `warn` or `bad` only when it is true. |
| `scope` | Where this session sits in the bigger plan, as 3 to 5 steps left to right: `name` plus `state` (`done`, `now`, `next`, `later`); exactly the session's own step is `now`. Take the steps from the project's plan, TODO pin, or promised dates, never invent a phase. Leave it out when the session was a one-off with no plan around it. |
| `done` | One item per real piece of work, in the order it happened. `what` in plain words (no function names, no internal labels); `proof` is how we know: a commit, a deploy, a test count, a page checked. Work that did not finish is NOT here; it goes to `issues` or `mine`. |
| `decisions` | Every choice the user made this session: `choice` in plain words ("You chose X"), `recorded` naming the file that holds it. Empty list when none. |
| `issues` | What went wrong or is still weak, blockers included. `what` says the problem; `effect` says how it hits the real document or person. Empty list when there is none; never invent one to fill the box. |
| `yours` | Steps only the user can take (a decision, a message to someone, an access grant). Each one is a full sentence they can act on without opening another file. |
| `mine` | What Claude does next session. Must match TODO.md and its pin. |
| `next` | 1 to 3 options for the next move, each `title`, `what` (what gets done), `changes` (what the user gains or loses), optional `command`. Mark exactly one `pick: true` when there is a real recommendation. |
| `recommendation` | Which option and why, in one or two sentences. |
| `saved` | One tile per place written (repo notes, project notes, memory, TODO, task board, status sheet, improvement report, a deliverable): `where`, a `state` chip (`updated`, `pushed`, `unchanged`, `uncommitted`, `refused`, `skipped`, `not-due`), a one-line `detail`, optional `items` (sub-points) and `path`. A refusal or a "left uncommitted" gets its chip; never hide it in the detail. |
| `pages` | Every explainer page or deliverable this session wrote: `title`, absolute `path`. They become clickable links. |
| `cleaned` | Under `/close-session` only: what its steps found running, stopped and cleaned up, and the old-sessions line. |

**Writing rules.** Short sentences, small words. Say what happened to the thing, not to the code. No em dashes. Hebrew stays Hebrew; the page sets direction itself. Backticks mark a path or command.

## 2. Build, look, open

```sh
python3 ~/.claude/skills/session-summary/build_summary_page.py <tmp>/summary.json \
  --out-dir ~/.claude/projects/<X>/session_summaries --open
```

- It prints the page path. Exit 2 means a field is missing or wrong; the message names every problem. Fix the JSON and run again. Never skip the page because the script refused.
- Take a 1280px screenshot (headless Chrome `--window-size=1280,1700 --screenshot=...`) and LOOK at it before reporting: every section filled, the pick marked, nothing cut off. If no browser can run, say so.
- `--open` opens it in the user's browser.

## 3. Name it in the report

Give the page's absolute path on its own line.
The chat lines stay short: the page is where the detail lives, so do not paste its sections into the chat.

## Changing the page

The script is the one owner of the look. To add or change a section, change all four together, in one commit:

1. `validate()` in `build_summary_page.py`: what the field must hold, with a message naming the problem.
2. `render()` and `CSS`: the section itself, light and dark (`prefers-color-scheme`). Optional sections drop out when empty, and the section numbers close up by themselves.
3. `test_build_summary_page.py`: a test that fails without the change, plus a refusal test for a bad value. Run `python3 test_build_summary_page.py`.
4. `reference/example.json` and the field table above, so the example still renders (a test checks it) and the next caller knows the field exists.

Then render the example, and look at it at 1280px in light and dark before calling it done.
