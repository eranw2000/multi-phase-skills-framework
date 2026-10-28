---
model: opus
name: plan-status-sheet
description: "Keep a project's plan-status Google Sheet in step with its plan and its repository: one Sheet per project, one link that never changes, rewritten in place from the project's own row data. It checks that every numbered plan section has a row or a written reason, that every date is a real past date read from a commit or a deploy, and that the ten shared columns are intact, then rewrites both tabs and reads them back. Use when the user says 'update the plan sheet', 'sync the plan status', 'set up a plan status sheet', 'refresh the project status sheet', or asks where a project stands against its plan. Not for a manager-facing page with headline numbers."
---

# Plan status Sheet

One Google Sheet per project, at one address that never changes, holding a row per
feature of the plan.

## Why a Sheet and not a file

A workbook gets copied, mailed, and goes stale in somebody's downloads folder, and the
copy in front of a reader is never the one that was rebuilt. A Sheet has one link, so a
link handed out once keeps working, and Google keeps the version history for free.

## What this owns, and what it must never do

It owns the Sheet and the checks. It does NOT decide that a feature is finished. A
person or a session makes that call and edits the project's own row data. What this
enforces is that the claim is checkable.

**Never edit a cell in the browser.** Every run replaces every cell, so an edit made
there is lost at the next release and nobody sees it go. Edit the rows in the project.

## The checks, and why each exists

- **Plan coverage.** Every numbered heading in the plan must have a row, or be written
  down in the config as deliberately having none, with the reason. This is the half
  that actually keeps the table in step: work gets added to a plan and the table does
  not notice.
- **Dates.** Every row carries a date or an explicit blank, and a date must be a real
  date that is not in the future. A date is a claim about a record, so it comes from
  `git log -1 --date=short` or from the deploy that carried it, never from memory.
- **Schema.** The ten shared columns are present and in order. A project may append its
  own columns. It may not reorder or drop these, because the summary reads them by
  position.

- **Dependencies.** Every row says what must happen first. WARNS rather than fails,
  so an existing table with empty cells is not blocked.
- **Blocker measurement.** A `BLOCKED` cell must say when the blocker was last measured. A
  blocker copied forward is a claim, not a fact. It matches the MECHANISM, a measurement
  word plus a real past date, rather than one phrasing, because honest cells word it
  more than one way.
- **Cross-references.** A blocked row names its fix and that row exists. A dangling
  cross-reference is worse than none.
- **The pinned cell.** `PINNED_CELL = (feature, column index, exact text)`. Every other
  check here can pass over an empty Sheet; this one cannot. Expect it to fire when you edit
  the cell it pins. That is the control working: update the text and move on.
- **TODO coverage.** Reports which unfinished rows the project's `TODO.md` does not name.
  It REPORTS rather than warns: a TODO is prose and the same work is often written there in
  other words, so a guard keyed on the name would fire on well-formed input.

A push runs the checks first and refuses to write when one fails. A Sheet built from
rows that failed their own checks is worse than no Sheet, because it looks
authoritative.

## Which plan, when a project tracks several

A project's Sheet belongs to an INITIATIVE, not to a filename, so the link survives every
rewrite of that initiative's plan. Declare them in the config:

```python
INITIATIVES = [
    {"name": "standardization", "plan": "PLAN_....md"},
    {"name": "search", "plan": "other_plan.md", "rows": "ROWS_SEARCH"},
]
```

A config with no `INITIATIVES` declares one, synthesized from `PLAN`, so a single-plan
config needs no edit and keeps its link.

Three values cannot be shared between initiatives, and each may be a dict keyed by
initiative name instead of a single value: `DOC_TITLE` (the Sheet's own title),
`SECTIONS_WITHOUT_ROWS` (a second plan has its own numbering and its own reasons), and
`PINNED_CELL` (a pin naming the first plan's row would fail the second plan outright).
The flat form still works everywhere. The two dict shapes are told
apart by their keys: initiative names against section numbers.

**Several initiatives in ONE Sheet (one link).** `GRID_TAB` and
`SUMMARY_TAB` may also be dicts keyed by initiative name. Record the same `spreadsheetId`
under each initiative in `plan_status_gsheet.json` (keep the first one named `default` so it
still reads the bare id), and each push writes only its own tab pair. A push REFUSES when
two initiatives on one Sheet resolve to the same tab, because each push would overwrite the
other's table.

With several present and none named, the run PRINTS the picker and exits **4**. That is the
caller's cue to ask, never to pick. Name one with `--initiative <name>`.

**A superseded plan is refused, not warned about.** A plan header's own
`**Plan it continues:** <path>` line makes a chain, and a file named by another file's
chain is an ancestor. Pointing a push at an old version would rewrite the Sheet
against a plan that has since been replaced. Only
the initiative you actually SELECT is refused; a stale sibling warns, because failing every
initiative over one bad entry punishes the whole file for one line.

## The derived columns

Declare `SOURCES = {feature: branch}` in the data module and four columns are appended and
filled from `git` and `gh` at push time: the branch, the pull request state, the head commit
and whether it is on main. The facts that rot stop being typed into the prose.

A squash merge rewrites commits, so a merged branch is never an ancestor of main. The pull
request is the authority on whether the content landed; ancestry alone would report "no"
about work that shipped weeks ago. The suite count stays hand-written, because it comes from
running tests rather than from git.

## Running it

```
S=~/.claude/skills/plan-status-sheet/sync.py
P=python3

$P $S --project <name> --check     # offline. No token, no network, no writes.
$P $S --project <name> --push      # check, rewrite the Sheet, read it back.
$P $S --project <name> --status    # the link and the headline counts.
$P $S --project <name> --initiative <x> --push   # when it tracks several
$P $S --repo <path>   --push       # find the project from a repository path.
```

`--project` takes a project name, a unique fragment of it, or a path. `--repo` exits 3
when no project keeps a Sheet for that repository, which means skip, not fail. A Sheet that
also tracks packages built in a SECOND repository declares it in `HAND_UPDATED_REPOS`: that
repository's releases then find the Sheet and are told to set their hand-kept rows, instead
of hearing "no Sheet" and leaving them stale.

## Updating a project when a feature moves

1. Edit the row in the project's data module. Change the status, and set the date from
   a record. Say which record in a comment beside it.
2. Run `--push`.
3. Read what it printed. It names the rows that are blocked, the rows one setting away,
   and any plan section that has no row.

## Setting up a new project

1. `--setup` writes `plan_status_config.py` into the project data folder and stops.
2. Fill it in: the module that holds the rows, the plan file (or `INITIATIVES`), the
   repository path, and a `PINNED_CELL`. You do NOT write `sheet_rows()`: the skill owns
   the mapping, and the shape is eight fields per row plus a `DATES` map keyed by feature
   name, so per-project copies cannot drift apart. Define
   `sheet_rows(data)` in the config only if this project's shape genuinely differs, and it
   then overrides the skill's.
3. Run `--check`, read the coverage report, and write a reason for every numbered
   section that deliberately has no row.
4. Run `--setup` again. It creates the Sheet, records the id, and pushes.

## Google sign-in, once per machine

`--check` needs no Google account. `--setup` and `--push` need your own OAuth client and a
token minted from it. Both live in `~/.config/plan-status-sheet/`, or in the folder named
by `PLAN_STATUS_GOOGLE_DIR`. The steps follow Google's Python quickstart for the Sheets
API (https://developers.google.com/workspace/sheets/api/quickstart/python), which has the
screenshots.

1. In a Google Cloud project, enable the Google Sheets API:
   https://console.cloud.google.com/flows/enableapi?apiid=sheets.googleapis.com
2. Configure the OAuth consent screen under Google Auth platform > Branding
   (https://console.cloud.google.com/auth/branding). Under Audience, Google's quickstart
   picks Internal, and says an app used outside your Workspace organization needs the
   External user type instead.
3. Under Google Auth platform > Clients (https://console.cloud.google.com/auth/clients),
   create a client with Application type Desktop app. Download its JSON file and save it
   as `~/.config/plan-status-sheet/credentials.json`.
4. Install the client libraries:
   `python3 -m pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib`
5. Run `python3 mint_token.py` in this folder, in a terminal on a machine with a browser.
   It opens Google's consent page and writes `sheets_token.json` beside the client file,
   readable only by you. It asks for one scope, `spreadsheets`, which Google describes
   as "See, edit, create, and delete all your Google Sheets spreadsheets".

Enabling the API and consenting to the scope are separate steps. If a push stops with
"The Google Sheets API is not switched on", do step 1 for the project that owns your
client, wait a minute, and run it again; the token does not need minting again.

Treat both files as secrets: never commit them, paste them, or print their contents.

## After changing anything here

```
python3 ~/.claude/skills/plan-status-sheet/test_sync.py
```

Offline, and every check is paired with a control that must fire.

## Four Sheets API behaviours to know

- A merge that crosses the frozen-column line is refused. The banner therefore starts in
  column C, inside the unfrozen block.
- Google's own "fit rows to data" is inert for wrapped text: a long wrapped cell comes
  back at the default one-line height. So no row height is ever set, and the rows are
  dropped and regrown to make sure none carries one.
- Clearing the freeze must be its own request, before the rows are dropped. Google
  refuses to delete every unfrozen row, and doing both in one request is still refused.
- Never delete a tab. That changes the tab id and breaks a saved link.

## Not this skill

A manager-facing page with headline numbers and cards is a different job.
This builds an engineer-facing table you filter, sort and edit. Both can exist for one
project and they answer different questions.
