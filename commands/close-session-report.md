---
model: sonnet
description: "Run the full /close-session workflow, then write everything it produced (files changed, memory saved, TODO items added, resources stopped, what was skipped) to a dated session record file."
argument-hint: "[optional output path, or a project name]"
---

Run `/close-session` end to end, then save a record of everything it produced to a file, so the close-out outlives the terminal scrollback.

The skill does the work. This command adds one thing: a durable record of it.

Do not restate or reimplement the close-session steps here. Read `~/.claude/skills/close-session/SKILL.md` and follow it verbatim, then capture the result. If the two ever disagree, the skill wins; it owns the workflow and this command owns only the file.

## Order of operations

1. Run the close-session workflow to completion.
2. Then write the record, from what actually happened.

Never draft the record first and fill in the work afterwards. A record written in advance describes the run you intended rather than the run you got, and the two part company the moment a step is skipped, fails, or finds nothing worth saving. The file is a record, not a plan.

## Where the file goes

Default path:

```
~/.claude/projects/<project>/session-closeouts/close-session-<YYYY-MM-DD>-<HHMM>.md
```

`<project>` is whatever close-session resolved in its step 1. Do not resolve it a second time by your own route: if this command picked a different project than the skill did, the record would describe one project while the saves landed in another. Take the answer from the skill and reuse it.

The directory sits beside the project's `TODO.md`, which close-session already targets, so it exists on any machine without configuration. Create `session-closeouts/` if it is not there. Get the timestamp from `date +%Y-%m-%d-%H%M`; if that exact file already exists, append `-2`, `-3` and so on rather than overwriting a sibling run.

`$ARGUMENTS` is optional. If it contains a `/` or ends in `.md`, treat it as the output path and use it instead of the default. Otherwise treat it as a project name and pass it to close-session's project resolution. State which reading you took in one line, so a mistyped path does not silently become a project name.

## Write the record even when the run stops early

close-session halts if a save step fails, and that is the case where the record is worth most. Write the file anyway, put the failure in the Outcome section at the top, and leave every section below it honest: a run that stopped at step 2 has no cleanup to report, so its Cleanup section says so instead of being padded to look complete.

## The record

Use this structure. Keep the headings even when a section is empty, so a later reader can tell the difference between nothing happening and nothing being checked.

```markdown
# Session close-out: <project>

- When: <YYYY-MM-DD HH:MM>
- Working dir: <cwd>
- Repo: <name>, branch <branch>, HEAD <short sha>
- Outcome: <completed | stopped at step N>

## Outcome
<One or two lines. If the run stopped early, why, and what is now half-done.>

## Project CLAUDE.md
Path: <path>
- <section heading touched>: <one to three lines on what changed>

## Global CLAUDE.md
<What was added, or: None, nothing applied across all projects.>

## Memory
Path: <memory dir>
- <file.md> (created | updated), type <user | feedback | project | reference>: <one line>
- Index line added: <the pointer written into MEMORY.md>

## TODO items added
Path: <path to TODO.md>
- <bucket>: <the item, verbatim as written to the file>

## Cleanup
Stopped:
- <pid> <command> (why this one belonged to this session)
Left running:
- <what> (why it was not certain to belong to this session)

## Not done, and unverified
- <a step skipped, and why>
- <anything the run could not confirm>

## Resume point
<One or two lines: what the next session picks up, and where.>

## Final summary, as reported in the session
<The closing message from the close-session run, verbatim.>
```

Drop the Repo line when the project has no linked repo. Every other heading stays.

## What goes in, and what deliberately does not

**Record the headings, paths and a short gist for anything that now lives in another file.** A CLAUDE.md section or a memory file is already saved; copying its prose into the record makes a second copy that goes stale as soon as the original is edited, and a later reader has no way to tell which one is current. Point at it instead.

**Record verbatim only what exists nowhere else**: the TODO lines as they were written, and the final summary from the session. Both are short, and the summary is otherwise lost with the scrollback.

**Record what did not happen.** A skipped step, a process left running because it could not be attributed to this session, a save that found nothing worth keeping. An empty section reads as "checked, nothing there" only if the run says so; otherwise it reads as "not checked", and the difference matters to whoever picks the project up.

**Never pad.** A section with nothing in it gets one line saying so. Do not invent a resume point for a session that finished cleanly, and do not promote session noise into an open action item to make the file look busier.

## Verify before reporting

After writing, read the file back and check two things:

1. **Every path it names exists on disk.** A record claiming a memory file that was never created is worse than no record, because it is the copy a future session trusts. Where a path is missing, fix the record rather than the claim.
2. **Every section corresponds to something the run actually did.** If the record says a CLAUDE.md section was updated, that heading should be in the file. Reading the record back is the only check here; nothing else looks at it.

Report the failure and the path if either check fails. A record that cannot be trusted should not be reported as saved.

## Final message

Close with the same confirmation close-session gives, plus the record path on its own line so it can be opened directly:

> Context saved (CLAUDE.md + 1 memory). Added 3 open items to TODO.md (2 Active, 1 Parked). Stopped the dev server on :8002.
> Record: ~/.claude/projects/my-project/session-closeouts/close-session-2026-08-12-1740.md

If the run stopped early, that goes first, before the summary, on its own line. A tidy report reads as success however carefully the caveat is worded further down.

## Do not use this command if

- You want the close-out without a file. Use `/close-session`.
- You want to save context without cleanup. Use `/save-context`.
- You are not actually at the end of the work. Closing mid-task loses context, and a record of a half-closed session invites a future reader to trust it.
