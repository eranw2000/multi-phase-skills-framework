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

Read this session's own transcript from disk, found by its path or by asking, never the newest file on the machine, because after a compaction the conversation is only a summary.

**Read `~/.claude/skills/save-context/reference/1-recover-the-session.md` now, in full, and follow it. It is this step's full text; the line above is only a summary and is not enough to act on.**

### 2. Identify the project and every file this save can write

- Determine which project was worked on, from the conversation and the working directory.
- **The notes file** is `~/.claude/projects/<X>/CLAUDE.md`. Create it if absent. The folder name often does not match the repo name, so `ls ~/.claude/projects/` and match; never string-build the path.
- **The repo file** is the `CLAUDE.md` at the root of the project's code repository, when the project has code. Check whether it exists. It is version controlled and it loads for any session launched inside the repo, which the hidden data-dir file does not, so a build command, a test command or a code convention belongs there and nowhere else.
- Tier by specificity: global, then the project notes file, then the repo file. A rule lives at the most specific tier that still applies.

### 3. Route each item before you write it, and measure first

Measure every always-loaded destination first, then send each item to the most specific file that still fits, never the same rule in two places.

**Read `~/.claude/skills/save-context/reference/3-route-and-measure.md` now, in full, and follow it. It is this step's full text; the line above is only a summary and is not enough to act on.**

### 4. Update the project CLAUDE.md

Add the decisions, fixes, gotchas, commands and status changes that step 3 routed here, updating existing sections rather than duplicating them.

**Read `~/.claude/skills/save-context/reference/4-project-claude-md.md` now, in full, and follow it. It is this step's full text; the line above is only a summary and is not enough to act on.**

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

### 7. Ask whether this session exposed a fault in the harness itself

When a trigger fired this session, ask the user once whether to run `/improve-dev-workflow` now; with nobody to ask, run it.

**Read `~/.claude/skills/save-context/reference/7-harness-fault.md` now, in full, and follow it. It is this step's full text; the line above is only a summary and is not enough to act on.**

### 8. Capture the session's open action items into the project TODO

Add every still-open action item to the right bucket of the project TODO.md, correct items this session made false, and run the auto-sync once.

**Read `~/.claude/skills/save-context/reference/8-open-action-items.md` now, in full, and follow it. It is this step's full text; the line above is only a summary and is not enough to act on.**

### 9. Write the next-session pin

The last thing this session owes the next one is a straight answer to "what do I do now". Write it into the project's `TODO.md` pin block (`## >>> NEXT SESSION: start here <<<`), replacing whatever is there.

**The pin block's format is owned by `~/.claude/skills/todo/todo-format.md`. Read it and follow it.** In short: one action, the exact command, twelve lines or fewer, a blocking fact on the first line if something is built but not in front of the user, and none of your own vocabulary. The reader did not sit through this session and reads the pin in a hurry.

Skip this only when the session genuinely ends with nothing to do next, and then remove the stale pin rather than leaving it to misdirect the next session.

### 10. Read back what you wrote

Re-read every span you edited, re-measure each file, and grep for stale status words and self-moving figures this session made false.

**Read `~/.claude/skills/save-context/reference/11-read-back.md` now, in full, and follow it. It is this step's full text; the line above is only a summary and is not enough to act on.**

### 11. Report what was saved

Open the report with these five lines, each one sentence in plain words, each naming the file it was saved to (or "none"):

- **Complete:** what this session finished, and which TODO items were marked done
- **Current work:** what is still in flight, and where it stopped
- **Decisions:** what was decided, and why
- **Blockers:** what is stuck, and what would unstick it
- **Next steps:** the next action, which is the pin's

Then the detail:

- Which source you reviewed: the transcript, or the live context
- Which CLAUDE.md files were modified, and what changed in each
- Which satellite or rules file received evidence, and which memory files were created or updated
- The size of each always-loaded file you touched, and whether any is over its limit
- **The open action items added to `TODO.md` and the bucket each went in** (or "nothing was left open"), plus whether the cross-project index and the project memory were auto-synced
- Whether a harness fault fired step 7, which artifact owns it, whether the user chose to improve the workflow now, and what `/improve-dev-workflow` changed (or "no harness fault this session", or "improvement declined, filed as an open item")
- Anything you corrected because it had become false
- The one action the pin now names

## Key Principles

- Capture the **why** behind a decision, not only the **what**
- Do not save ephemeral task detail; save durable knowledge
- Do not duplicate what git history or the code already says
- Prefer updating an existing section over creating a new one
- If nothing meaningful was discovered, say so; do not pad the files with noise
