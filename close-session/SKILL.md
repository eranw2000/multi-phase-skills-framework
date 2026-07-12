---
model: sonnet
name: close-session
description: End-of-session save AND cleanup — runs the full save-context workflow (project CLAUDE.md, optional global CLAUDE.md, MEMORY.md files + index), then cleans up the shells, dev servers, and background agents/tasks this session spawned. Does NOT close the Terminal window. Use when the user says "this thread is done", "close this session", "end session", "end of session", "save and close", "wrap up and exit", "we're done, close this", or any variant signaling "save context and tidy up this session". For save-only without cleanup, use /save-context instead.
disable-model-invocation: false
---

# Close Session — save context, then clean up the session's resources

Two-stage skill: do everything `/save-context` does (CLAUDE.md + MEMORY.md updates), then tear down anything THIS session started (background shells, dev servers, background agents / tasks). It does NOT close the Terminal window — that behavior was removed (a global flag could close the wrong window, especially from a detached/background session).

## Steps

### 1. Run the full save-context workflow
Execute every step from `~/.claude/skills/save-context/SKILL.md` verbatim:

1. **Identify the active project** from conversation context and working directory. Locate the project's CLAUDE.md (in `~/.claude/projects/<X>/CLAUDE.md` for project-data, or the repo root for repo-conventional). If it doesn't exist, create it.
2. **Update the project CLAUDE.md** with anything new from this conversation. First ask: what did I have to figure out this session that wasn't in CLAUDE.md and cost me time? Capture that first. Then: decisions made, features implemented, bugs fixed, gotchas discovered, operational commands & environment (build/test/run/deploy commands, env setup, venv or Docker quirks discovered this session), configuration changes (IDs, endpoints, env vars, column names), status updates (mark "Planned" items as implemented, bump versions), lessons learned. Don't duplicate; update existing sections; remove outdated content. Keep it factual and concise.
3. **Update `~/.claude/CLAUDE.md`** ONLY if something from this conversation applies across ALL projects (new workflow patterns, user's preferences, credential/access updates, cross-project references). Skip otherwise — no noise.
4. **Update MEMORY** in `~/.claude/projects/<index-dir>/memory/` (where `<index-dir>` is the dash-encoded home path, e.g. `-Users-jdoe` for `/Users/jdoe`; derive it from `$HOME`) for any new user / feedback / project / reference facts. Keep the split simple: durable facts and discoveries go in memory, behavioral rules and conventions go in CLAUDE.md, and never duplicate the same thing in both. Update the `MEMORY.md` index with one-line pointers (`- [title](file.md), hook`, ≤150 chars). Don't duplicate what's already in CLAUDE.md.

### 2. Capture the session's open action items into the project TODO
Before reporting, sweep this conversation for action items that are still open at close time: work that was discussed, planned, deferred, parked, or flagged as a follow-up but NOT finished in this session. Skip anything already completed and anything that's just session noise.

Run the `todo` skill's workflow (`~/.claude/skills/todo/SKILL.md`) against the active project to record them:
- Resolve the project the same way step 1 did (don't re-ask if step 1 already resolved it), and target its `~/.claude/projects/<X>/TODO.md`, creating it from the template if absent.
- For each open action item, `add` it to the right bucket: in-flight or next-up work → **Active**; not-yet-started but intended → **Queued**; blocked or contingent → **Parked**. Carry a due date as `(due YYYY-MM-DD)` when the session named one.
- Before adding, check the existing items so you update or skip duplicates instead of stacking a second copy. Honor the file's existing bucket structure (some files use curated bucket names) per the todo format rules.
- Run the todo skill's auto-sync (cross-project index + project memory) once after the adds, not per item.

Edit the real `TODO.md` markdown file — never satisfy this with the ephemeral TodoWrite tracker. If nothing is genuinely open, write nothing and say so in the report.

### 3. Report what was saved
Print a tight summary (5–10 lines): which files changed, which sections, any new memory files created, and the open action items written to `TODO.md` (count + buckets). If nothing meaningful was discovered, say so plainly — don't pad.

### 4. Clean up session-spawned resources (ONLY after saves succeed)
Tear down anything THIS session started, so nothing keeps running after the thread ends. Be conservative: only kill processes/jobs this session is responsible for, never unrelated user processes.

- **Background dev servers / app processes** this session launched (e.g. `manage.py runserver`, `npm run dev`, `vite`, a watch process). Identify them by the port/command you started, confirm they match what you launched, then stop them (`kill <pid>`).
- **Background Bash jobs** still running from this session (pollers, `tail -f`, monitors). Stop them.
- **Background agents / tasks** this session spawned that are still active.
- **Temp scratch** in `$CLAUDE_JOB_DIR/tmp` is auto-cleaned; don't bother.

If you're unsure whether a process belongs to this session, leave it and say so in the report rather than risk killing something the user needs.

### 5. Final assistant message
End with a short confirmation listing what was saved, what went onto the TODO, and what was cleaned up, e.g.:

> Context saved (CLAUDE.md + 1 memory). Added 3 open items to TODO.md (2 Active, 1 Parked). Stopped the dev server on :8002 and the background poll job. This session is wrapped up — you can close the window whenever.

Do NOT attempt to close the Terminal window or drop any flag file.

## Don't use this skill if
- You only want to save context without cleanup — use `/save-context` instead.
- You're not actually at the end of the work. Closing mid-task loses context.
- A save step failed. Surface the error and stop; fix it before wrapping up.
