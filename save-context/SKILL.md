---
model: opus
name: save-context
description: End-of-session context save. Reads the session transcript so a compacted conversation cannot shrink what gets saved, routes each discovery to the file that will actually be read (project CLAUDE.md, global CLAUDE.md and its satellites, a path-scoped rule, a skill, or memory), measures the always-loaded files before adding to them, captures the session's still-open action items into the project TODO buckets, writes the next-session pin, and reads back what it wrote. Use when the user says "save context", "save session", "/save-context", or wants to capture this session's learnings without closing the session. For the same save PLUS shutting down the session's servers, jobs and agents, use close-session instead.
disable-model-invocation: false
---

# Save Session Context

Persist everything a future session needs from this one. Runs at the end of a conversation, and does not close it.

Three things decide whether this save is worth anything, and all three happen before a single word is written: read the real conversation, route each item to a file that will actually be read, and measure the destination before adding to it. Steps 1 to 3 do those. Do not skip them to get to the writing.

**The save runs in ONE turn, start to finish. Never end the turn to wait for background work.** A command that outlives the Bash tool's default two minutes is moved to the background, and ending the turn to wait for it splits the save in two: its completion notice arrives as a new entry between the save and the rest of it. Anything that reads "the save is the last thing that happened" then treats the save as overtaken, and a session interrupted in that gap is left half saved.

**How to wait instead:** give any command that may run long an explicit `timeout` (up to 600000 ms) so it stays in the foreground. If it can run longer than that, start it in the background and wait on its output file with `Monitor` and an until-condition, still inside the turn. This covers every step.

## Steps

### 1. Recover the full session before you review it

A long session compacts, and compaction replaces the conversation with a summary. Instructions come back from disk; the conversation does not. So on the sessions that most need saving, "review the conversation" reads a retelling, and the specifics this save exists to rescue are the first thing a summary drops.

The transcript on disk is complete whether or not that happened. Read it rather than your own recall. It is a `.jsonl` file with one JSON object per line and is often large, so read it in pieces or hand it to a subagent rather than loading it whole.

**IDENTIFY the transcript, do not take the newest.** `ls -t ~/.claude/projects/*/*.jsonl | head -1` reads across EVERY project, so it hands you whichever session on this machine wrote last, which is routinely a parallel session in another repository. A save built on a stranger's transcript is worse than a save built on your own recall, because it reads as evidence. In order:

1. **The session's own path**, when a hook envelope or the caller gave it. That is the only answer with no guess in it. Read that file.
2. **Otherwise list the candidates under THIS project's encoded directory only**, newest first, and ask which one, naming your best guess as the recommendation:

```sh
CWD="<the project launch directory>"
ls -lt "$HOME/.claude/projects/$(printf '%s' "$CWD" | tr -c 'A-Za-z0-9' '-')"/*.jsonl
```

3. **When there is no one to ask, stop and report `no transcript identity`** with the candidates you saw, rather than picking one. A save is the record of what happened, so a wrong source is a wrong record that the next session trusts.

Never widen the glob back to `projects/*/` to find "a" transcript. One match in the project directory is the answer; none means this directory is not where the session ran, which is a fact to report.

Say in the final report which source you reviewed, the transcript or the live context. A save built on a summary is worth less, and the reader is entitled to know which one they got.

### 2. Identify the project and every file this save can write

- Determine which project was worked on, from the conversation and the working directory.
- **The notes file** is `~/.claude/projects/<X>/CLAUDE.md`. Create it if absent. The folder name often does not match the repo name, so `ls ~/.claude/projects/` and match; never string-build the path.
- **The repo file** is the `CLAUDE.md` at the root of the project's code repository, when the project has code. Check whether it exists. It is version controlled and it loads for any session launched inside the repo, which the hidden data-dir file does not, so a build command, a test command or a code convention belongs there and nowhere else.
- Tier by specificity: global, then the project notes file, then the repo file. A rule lives at the most specific tier that still applies.

### 3. Route each item before you write it, and measure first

Two things decide where a discovery goes: what kind it is, and how much room the destination has. Do both now, because a measurement can change the destination.

**Measure first.**

```sh
wc -c ~/.claude/CLAUDE.md
wc -c ~/.claude/projects/<X>/CLAUDE.md
wc -l -c ~/.claude/projects/<X>/memory/MEMORY.md
```

The limits: the global file at the size target you keep for it; a project notes file at the threshold that project's own file states, which differs per project, so read it there; the memory index at 200 lines and 25KB, which the loader truncates in silence.

**A file already over its limit does not get another line from this save.** Put the content in the matching satellite, and say in the report that the file is over and `/split-claude-md` is due on it.

**Then route.** Most specific destination that still fits, and never the same rule in two places:

- **Nothing the repository already answers.** A directory layout, a dependency list, an architecture the code states plainly. Do not write it anywhere.
- **A rule about how Claude should behave on this project**: the project notes file.
- **A build, test, run or deploy command, or a code convention**: the repo file, so a session launched in the repo gets it.
- **A rule that applies everywhere**: the global file, as ONE line, with the evidence in a satellite file beside it, one per topic (testing, deployment, a given SDK). Keep the rule always loaded and move only its dated evidence. Never put both halves in an always-loaded file.
- **A rule that fires on a file type rather than on a conversation**: a rule file in `.claude/rules/` with `paths:` frontmatter. It leaves the always-loaded set entirely, which is the cheapest destination there is. It is lost after a compaction until a matching file is read again, so send a rule here only when a file triggers it.
- **A multi-step procedure**: a skill, not a rule. Anything with an order of operations belongs in a body that loads when it is needed.
- **An observational fact about a system**: memory. If you split the memory index into topic indexes, file the row in the matching one. Only a fact that fires on any task belongs in `MEMORY.md` itself.
- **Project state**: always memory, never a CLAUDE.md.
- **An external pointer**, meaning a board, a dashboard or a service id: a memory `reference_*` entry.

The ownership test in one line: a rule about how to behave goes to a CLAUDE.md, a fact about a system goes to memory, and neither file repeats the other.

### 4. Update the project CLAUDE.md

Read the current file, then add what step 3 routed here.

As you scan, ask: what did I have to figure out this session that was not in the file and cost me time? Those are the highest-value additions for a cold start. Anthropic names four more triggers worth using: Claude made the same mistake a second time, a review caught something Claude should have known about this codebase, you typed the same correction you typed last session, or a new teammate would need this to be productive.

- **Decisions made**: design choices, trade-offs discussed with the user, and the why behind each
- **Features implemented**: what was built and how it works
- **Bugs fixed**: what went wrong, the root cause, how it was resolved
- **Gotchas discovered**: non-obvious behavior, edge cases, things that broke unexpectedly
- **Operational commands and environment**: build, test, run, deploy, env setup, venv or Docker quirks discovered this session
- **Configuration changes**: new IDs, endpoints, env vars, column names, API details
- **Status updates**: mark planned items as implemented, update version numbers
- **Lessons learned**: what worked, what did not, what to avoid next time

Do not duplicate what the file already says. Update the existing section when the information changed, and remove what is now outdated. Keep it factual and concise, in the file's existing structure and style.

### 5. Update the global CLAUDE.md and its satellites

Only for what applies across all projects, and only for what step 3 routed here:

- **A workflow pattern** that holds everywhere, such as a deployment technique or an API access method
- **The user's preferences** on working style, communication or tool choice
- **Credential and access updates**, such as a new tenant id, app registration or configured CLI
- **A cross-project reference** discovered this session

Write the rule in `~/.claude/CLAUDE.md` and the dated evidence in the satellite, then add the one-line pointer to the satellite. If nothing is globally relevant, skip this step. Do not add noise to the file every session reads.

### 6. Update memory

Save or update a memory when the session produced one of these, and it is not already in a CLAUDE.md:

- New information about the user's role, preferences or expertise, which is a `user` memory
- Guidance on how to approach work, which is a `feedback` memory, with the why
- Project context not derivable from code or git history, which is a `project` memory
- An external resource pointer, which is a `reference` memory

File the index row in the matching topic index from step 3 when you keep one, not in `MEMORY.md`, unless the entry fires on any task. Check for an existing file that already covers the fact and update that one rather than creating a second. Delete a memory that turns out to be wrong.

Then re-measure the index. `MEMORY.md` is truncated in silence past 200 lines or 25KB, and the rows that vanish are the ones at the bottom.

### 7. Capture the session's open action items into the project TODO

Sweep the session for action items that are still OPEN: work discussed, planned, deferred, parked or flagged as a follow-up but NOT finished. Skip anything completed and anything that is session noise.

Run the `todo` skill's workflow (`~/.claude/skills/todo/SKILL.md`) against the active project:

- Resolve the project as step 2 did, and target its `~/.claude/projects/<X>/TODO.md`, creating it from the template if absent.
- Add each open item to the right bucket: in-flight or next-up work to **Active**, not-yet-started but intended to **Queued**, blocked or contingent to **Parked**. Carry a due date as `(due YYYY-MM-DD)` when the session named one.
- Check the existing items first, so you update or skip a duplicate instead of stacking a second copy. Honor the file's existing bucket structure per the todo format rules.
- **Correct an item this session made false**, not only add new ones. An item that is wrong costs more than an item that is missing, because it sends the next session to redo finished work.
- Run the todo skill's auto-sync (`~/.claude/skills/todo/todo-format.md`, section "Auto-sync rule") ONCE after the adds, not per item. It updates the cross-project index and the project memory's open-items hook, which is the half a save otherwise leaves stale.

Edit the real `TODO.md` markdown file. Never satisfy this with the ephemeral TodoWrite tracker.

If nothing is genuinely open, write nothing and say so in the report. A save that invents an item to look thorough is worse than one that adds none.

**Why a save does this and not only a close.** A save is the only guaranteed end-of-session write. `/close-session` is skipped whenever the session keeps running, and a save is often run mid-session precisely because a close would tear down shells and jobs. So if the item sweep lives only in the close, every session that ends without one loses its open items and the pin becomes the sole record, which it is too short to be.

### 8. Write the next-session pin

The last thing this session owes the next one is a straight answer to "what do I do now". Write it into the project's `TODO.md` pin block (`## >>> NEXT SESSION: start here <<<`), replacing whatever is there.

**The pin block's format is owned by `~/.claude/skills/todo/todo-format.md`. Read it and follow it.** In short: one action, the exact command, twelve lines or fewer, a blocking fact on the first line if something is built but not in front of the user, and none of your own vocabulary. The reader did not sit through this session and reads the pin in a hurry.

Skip this only when the session genuinely ends with nothing to do next, and then remove the stale pin rather than leaving it to misdirect the next session.

### 9. Read back what you wrote

You have just edited files that every future session reads, and nothing has checked them. This step is short and it is not optional.

- **Re-read each span you edited.** An edit whose anchor starts mid-sentence duplicates a clause, and the write reports success either way.
- **Re-measure every file you added to**, against the same limits as step 3, and report the figures.
- **GREP for what this session made false; do not rely on noticing it.** "Look harder" is not a check, and this is the expensive kind of miss: the cold-start skills READ these claims and hand them to the user as fact. `new-session` pulls anything under "Deferred", "Next steps" or "TODO" and reports it as live open work; `project-status` reads the file for the deployed service id. So a stale line is not inert, it is amplified into a false answer. Run this and READ every hit:

  ```sh
  STALE='deferred|not deployed|never deployed|to go live|live deploy|no [a-z]+ service|nothing auto-deployed|no live|uncommitted|not pushed|not committed|not running|to ship|planned|still to do|next steps|TODO'
  grep -nEi "$STALE" ~/.claude/projects/<X>/CLAUDE.md

  # Memory files are NOT in one fixed directory: a memory store follows the launch
  # directory. Find every memory file that names the project, PRINT the list, then
  # grep those. An empty list means the name did not match, never that it is clean.
  MEM=$(find ~/.claude/projects -maxdepth 3 -path '*/memory/*.md' -exec grep -liE "<X>" {} +)
  echo "$MEM"
  [ -z "$MEM" ] && echo "NO MEMORY FILE NAMES <X> - try another spelling, do NOT read this as clean"
  [ -n "$MEM" ] && printf '%s\n' "$MEM" | while IFS= read -r f; do grep -nEi "$STALE" "$f" /dev/null; done

  grep -nEi "$STALE" ~/.claude/projects/<index-dir>/TODO.md | grep -i "<X>"
  ```

  **The memory file is not in one fixed directory.** A memory store follows the session's
  LAUNCH directory, so a project's memory can sit in any of several stores, and a project
  can have one in TWO stores. A glob that names one store matches nothing for the others,
  zsh prints `no matches found`, and an empty result reads exactly like a clean sweep. On a
  real setup that let a memory file say a pull request was "open, not merged" for five
  weeks after it merged, in a file recalled into OTHER projects' sessions. Print the resolved
  list every time; the print IS the control.

  **Use `find -exec`, never `grep $MEM`.** zsh does NOT word-split an unquoted parameter, so
  a two-file list reaches grep as one filename and the whole check dies with
  `No such file or directory`, which reads like a missing file rather than a broken check.

  **Run it on all three, because the same false claim copies itself across them.** On a real
  project, the notes file, the project memory AND the cross-project index row each
  independently said "deploy deferred" and "3 features still UNCOMMITTED" while the app had
  been live for a week. Fixing only the notes file leaves two artifacts still lying, and the
  memory one is worse, because it is recalled into sessions on other projects.

  Confirm each hit is STILL TRUE, and **rewrite the ones this session falsified rather than adding a new section beside them.** Expect legitimate hits; the check is that you read them, not that the count reaches zero. **Writing the new fact into a NEW file does not discharge this**, and that is the shape to watch for, because creating a thorough document feels like recording the fact. On a real project, a session deployed the app to production and wrote a full handoff document about it, while the notes file beside it went on saying no service existed yet and listing the deploy under "Deferred". A week later the user asked for the production server address and the project's own file answered wrongly.
- **GREP for a figure that moves by itself.** The stale check above matches status WORDS, so it cannot see a NUMBER that goes wrong while the file sits still. A download percentage, a free-disk reading, a days-since count, a live total: each is false within hours and nothing signals it. Run this too, and READ every hit:

  ```sh
  VOLATILE='(at|now|reached) [0-9]+ ?%|[0-9]+ ?% (complete|done|downloaded|uploaded|through|finished|of the way)|[0-9.]+ ?[KMGT]B (of|free|left|remaining)|(days|hours|minutes) (since|left|ago)|last (seen|run|deployed|updated|synced)|as of (today|now)|currently [0-9]|[0-9]+ (open|active|pending|queued|remaining)|already (fetched|downloaded|uploaded|processed)|[0-9]+h[0-9]+m'
  grep -nEi "$VOLATILE" ~/.claude/projects/<X>/CLAUDE.md
  grep -nEi "$VOLATILE" ~/.claude/projects/<X>/*.md
  ```

  **A hit is not a failure, it is a line to read.** Keep the figure only in one of two forms: it carries the moment it was read ("40 GB free, read 2026-08-27 at 22:00 UTC"), or the command that re-reads it sits beside it. Otherwise cut the moving half and keep the durable half: a self-moving figure does not belong in a document that sits still.

  Measured on a real project: a save wrote "at 58%, 8.0 GB of 13 GB, about 1h20m left" into the notes file and "of which 7.6 GB is already fetched" into a second document. Four minutes later the true figures were 62% and 8.5 GB and free disk had dropped a gigabyte, so both sentences were false before the session ended. The stale grep above ran over both files in that same save and reported no hits, because a moving number contains none of its status words. A bare `[0-9]+%` alternative was DROPPED from the pattern after it fired mostly on legitimate accuracy rates, weights and thresholds. The pattern fires on both of those sentences and stays silent on "150 GB/s", "36 GB unified memory" and "precision improved from 70% to 88%".

  **A claim ABOUT another document counts too.** The same save wrote "MODEL_RECOMMENDATION.md records 62 GB free" into the notes file minutes after correcting that very document to say 40. When one save edits two files that describe each other, re-read the describing sentence after the described file changes.
- **These files are edited by parallel sessions.** If a file changed under you between reading and writing, re-read it and re-apply your change. Never rewrite a block from a copy you took earlier in the session.

### 10. Report what was saved

- Which source you reviewed: the transcript, or the live context
- Which CLAUDE.md files were modified, and what changed in each
- Which satellite or rules file received evidence, and which memory files were created or updated
- The size of each always-loaded file you touched, and whether any is over its limit
- **The open action items added to `TODO.md` and the bucket each went in** (or "nothing was left open"), plus whether the cross-project index and the project memory were auto-synced
- Anything you corrected because it had become false
- The one action the pin now names

## Key Principles

- Capture the **why** behind a decision, not only the **what**
- Do not save ephemeral task detail; save durable knowledge
- Do not duplicate what git history or the code already says
- Prefer updating an existing section over creating a new one
- If nothing meaningful was discovered, say so; do not pad the files with noise
