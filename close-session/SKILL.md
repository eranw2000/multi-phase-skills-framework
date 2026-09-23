---
model: opus
name: close-session
description: End-of-session save AND cleanup. Runs the whole of /save-context by reading that skill's own file, never a copy of it, then cleans up the shells, dev servers, and background agents/tasks this session spawned. Does NOT close the Terminal window. Use when the user says "this thread is done", "close this session", "end session", "end of session", "save and close", "wrap up and exit", "we're done, close this", or any variant signaling "save context and tidy up this session". For save-only without cleanup, use /save-context instead.
disable-model-invocation: false
---

# Close Session: save context, then clean up the session's resources

Two-stage skill: do everything `/save-context` does (CLAUDE.md + MEMORY.md updates), then tear down anything THIS session started (background shells, dev servers, background agents / tasks). It does NOT close the Terminal window. That behavior was removed (a global flag could close the wrong window, especially from a detached/background session).

## Steps

### 1. Run `/save-context` in full

Read `~/.claude/skills/save-context/SKILL.md` and execute **every** step in it, in
order, following that file rather than any summary of it. Do not count its steps
here and do not name them: that file owns its own shape and changes without
telling this one.

**Do NOT restate those steps here, and do not re-run any of them below.** This file
used to carry an inline copy of four of them under the words "execute every step
verbatim". Save-context then grew and the copy silently described half the
skill, while this file separately repeated the TODO capture, the pin and the board
sync as its own step 2, so a close ran them twice and read the older wording for the
rest. One owner per rule: save-context owns the whole save, and this file owns only
what a close adds on top of it.

If any part of the save fails, surface the error and STOP. Do not clean up.

### 2. Clean up session-spawned resources (ONLY after the save succeeds)
Tear down anything THIS session started, so nothing keeps running after the thread ends. Be conservative: only kill processes/jobs this session is responsible for, never unrelated user processes.

- **Background dev servers / app processes** this session launched (e.g. `manage.py runserver`, `npm run dev`, `vite`, a watch process). Identify them by the port/command you started, confirm they match what you launched, then stop them (`kill <pid>`).
- **Background Bash jobs** still running from this session (pollers, `tail -f`, monitors). Stop them.
- **Background agents / tasks** this session spawned that are still active.
- **This session's scratch** in `$CLAUDE_JOB_DIR/tmp` is not cleaned up automatically in
  practice. It goes only when the job itself is deleted, and jobs are rarely deleted,
  so it piles up. List this session's scratch and copy anything durable into
  `~/.claude/projects/<project>/` before the thread ends. Leave re-derivable scratch
  (clones, build output, caches) alone. The next step sweeps the backlog.

**A COMMAND PATTERN MATCHES OTHER SESSIONS' WORK, so identify a process by its JOB
ID and not by what it is running.** On a real project, a close searched for its own
finished background work by tool name, and the search returned a LIVE reviewer that
belonged to another session, on a different repository, minutes into its run. Killing
it would have destroyed that session's review with no sign of what happened. Parallel
sessions run the same tools, so the tool name is the one thing that cannot tell them apart.

The check is free, because a backgrounded command carries its own job directory in
its command line: compare that against `$CLAUDE_JOB_DIR`. A process whose path names
a different job id is not yours, however exactly its command matches what you ran.
When the command line carries no job id at all, that is the "unsure" case above:
leave it and say so.

If you're unsure whether a process belongs to this session, leave it and say so in the report rather than risk killing something the user needs.

### 3. Sweep stale background jobs (cross-session hygiene)

Unlike the step above, this one is not about THIS session. A background job whose session ended without a terminal signal rests in state `blocked` forever and nothing expires it. That state is what the startup page shows as "Needs input", so it accumulates and competes with `TODO.md`, which is the list the user actually works from. On a real setup, dozens of jobs piled up over two months, and exactly ONE held a live uncaptured action.

Report it every time. The script only reports; removing a job is the user's own step:

```sh
python3 ~/.claude/skills/close-session/prune_stale_jobs.py
```

It reads `claude agents --json` and lists background sessions in `blocked` that started 14 or more days ago, one line each, followed by a `claude rm <id>` line per session. It never deletes anything. When it lists sessions:

- **Read them before anyone removes one.** The 14-day window keeps a job the user was blocked on last week out of the list, but an older one can still hold a real pending ask, a drafted message, or a question no TODO ever captured. Open it in the agent view (`claude agents`) and read its last message.
- **Capture anything real into the project's `TODO.md` FIRST** (via the `todo` skill), and save any drafted artifact into the project data dir so it does not die with the job.
- Then hand over the `claude rm <id>` lines for the ones that are safe to remove, or say to press Ctrl+X twice on them in the agent view. Do not run them yourself: removing a session discards its content.

### 4. Final assistant message

Save-context has already reported what it saved. **Add to that report rather than repeating it:** what was cleaned up, and the stale-job line. Then close with one short confirmation, e.g.:

> Context saved (CLAUDE.md + 1 memory). Added 3 open items to TODO.md (2 Active, 1 Parked). Stopped the dev server on :8002 and the background poll job. This session is wrapped up, you can close the window whenever.

Do NOT attempt to close the Terminal window or drop any flag file.

## Don't use this skill if
- You only want to save context without cleanup. Use `/save-context` instead.
- You're not actually at the end of the work. Closing mid-task loses context.
- A save step failed. Surface the error and stop; fix it before wrapping up.
