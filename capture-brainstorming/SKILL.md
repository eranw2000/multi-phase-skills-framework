---
name: capture-brainstorming
description: Capture a project's brainstorming into a single free-form BRAINSTORM.md handoff log (the findings and understandings reached, the facts the user shared, the directions taken and rejected, and the open topics the analyst still needs to resolve). Runs in two modes. Full capture mines BOTH the current conversation AND the project's past Claude session transcripts and writes the complete handoff so a later `/analyst` session starts warm. Checkpoint mode is a fast incremental save of just the new decisions, methods, facts, and open issues reached so far, built to run repeatedly during a long brainstorming or thinking session so nothing is lost if the session is interrupted or context is trimmed. Use full capture when the user says "save our brainstorm", "capture the brainstorming", "write up what we figured out", "prep this for the analyst", "save everything before we spec it", or wants to close out an exploratory phase. Use checkpoint mode when the user says "checkpoint this", "save our progress", "save what we have so far", and, at clear milestones during an extended brainstorm (a settled decision, a new open issue, a topic pivot), you may run a checkpoint on your own without waiting to be asked. Also surfaces concrete deferred action items that came up during the session and, on full capture, hands them to the `todo` skill so they land on the project TODO list instead of being lost. This is for brainstorming, design, and thinking sessions only. It is NOT for snapshotting code or a feature branch (that is a separate code-checkpoint step), and NOT for end-of-session context saving to CLAUDE.md or memory (use save-context or close-session).
disable-model-invocation: false
---

# Capture brainstorming — write the handoff log that warms up the analyst, and checkpoint along the way

Goal: produce one free-form `BRAINSTORM.md` that holds everything worked out across the project's brainstorming, in the live conversation and in earlier sessions, so the next phase (`/analyst`) opens already knowing the problem space instead of starting cold. During a long session, keep that file current with cheap incremental checkpoints so nothing is lost if the session is interrupted.

This is NOT the requirements doc. It does not impose the analyst's schema (FRs, NFRs, success criteria). It is a faithful, themed log of what was discussed and decided, ending with the topics the analyst still has to resolve. The analyst reads it, then interviews only the gaps.

## What goes in vs what stays out

In:
- Findings and understandings the user and Claude reached together.
- Facts, data, constraints, names, numbers, links, and examples the user shared.
- Methods, approaches, and rules-of-thumb worked out during the session.
- Directions chosen, and directions considered then rejected (with the reason).
- Open topics that must be resolved before requirements can be written.
- Concrete action items that came up but belong later in the process: a task someone must DO, not a question to decide. Keep these distinct from open topics. An open topic is something the analyst must decide; an action item is a deferred to-do (ask the client for X, set up service Y, verify Z after the next run).

Out:
- Solution architecture, library choices, schemas, file layouts (those belong to the architect, much later).
- Generic chitchat, abandoned tangents the conversation itself corrected, and restated boilerplate.
- Anything that is purely about how *this* capture session ran.

## Two modes: full capture vs checkpoint

This skill runs in one of two modes. Decide which before starting.

**Full capture** (default for explicit "capture the brainstorm" / handoff requests). Mines the current conversation AND past session transcripts, then writes or merges the complete `BRAINSTORM.md`. This is the heavy pass: it runs all of steps 1 through 7. Use it when closing out an exploratory phase or prepping for `/analyst`.

**Checkpoint** (lightweight, incremental, runs often). A fast save of only what the live conversation has reached since the last write: new findings, methods worked out, decisions, facts shared, and open issues. It does NOT mine archives. It runs steps 1, 2, and 5 only, then prints a one-line confirmation. The point is to lose nothing if the session is interrupted or context is trimmed, so it must stay cheap enough to run many times in a session.

### When to checkpoint proactively

A skill cannot fire itself on a timer. Once a brainstorming or thinking session is underway, treat periodic checkpointing as your own responsibility: run a checkpoint, at clear milestones, without waiting to be asked. Good triggers:

- A decision or direction was settled, or an earlier one reversed.
- A new open issue, risk, or unknown surfaced that must not be forgotten.
- The user shared concrete facts, data, constraints, or examples that future phases must not re-ask for.
- A method, approach, or rule-of-thumb was worked out.
- The discussion is about to pivot to a different topic.
- A long stretch of substantive back-and-forth has passed since the last checkpoint (use judgment; do not interrupt a fast exchange every turn).

Keep checkpoints silent and unobtrusive: a single short confirmation line, never a wall of text mid-conversation. If nothing materially new has been decided since the last checkpoint, skip the write and say nothing. When the brainstorm is finished or the user asks to hand off, switch to a full capture so the archive pass runs and the handoff is complete.

## Steps

In **checkpoint** mode, run only steps 1, 2, and 5 (logging any action items into section 7 of the file but NOT syncing them to the `todo` skill), then print the one-line confirmation from step 7. Reuse the project resolved earlier in the session (do not re-resolve or re-ask). In **full capture** mode, run all of steps 1 through 7.

### 1. Identify the project and the brainstorm topic

Derive `<project_name>` from context, in this order:
- The current working directory: a `~/.claude/projects/<X>/` data dir, a source repo dir (or a subdir of one), or a dash-prefixed leftover transcript folder all map to `<X>`. The canonical project dir is `~/.claude/projects/<X>/`.
- If the cwd is the home directory, bare `~/.claude`, or anything that does not map to a project, derive the project from the conversation topic instead. If still ambiguous, `ls -lt ~/.claude/projects/` and ask the user which project this brainstorm belongs to (offer the 3-4 most recently touched).

Also fix the **topic** of the brainstorm in one sentence, what subject the search should hunt for in past sessions (e.g. "the retrieval design", "the eligibility rules"). State the inferred project name and topic in one line, then continue without waiting for confirmation unless the project itself was ambiguous.

### 2. Harvest the current conversation first

Before touching any archive, distill the brainstorm in the live session: the findings, the facts the user shared, the methods worked out, the decisions, and the still-open topics. This is the highest-signal source and you already have it in context. Hold it as the spine of the doc; the archive pass only adds to it. In checkpoint mode, this is the only harvesting you do.

### 3. Find the project's past sessions

Two mechanisms, use both:

- **Full-text search across transcripts.** Call `search_session_transcripts` with 2-4 distinctive queries drawn from the topic and the project's vocabulary (project name, a domain term, a key proper noun). `include_archived: true`. Note which sessions hit.
- **Leftover transcript folders on disk.** Run `find ~/.claude -maxdepth 3 -type d -iname "*<project_name>*"`. The dash-prefixed folders (the dash-encoded form of the project's data-dir and source-repo paths, e.g. `-Users-<username>--claude-projects-<X>`, plus worktree variants) hold the `.jsonl` session transcripts and `subagents/*.jsonl`. The canonical `<X>/` folder with CLAUDE.md is NOT a transcript source, skip it here.

Collect the absolute paths of the candidate `.jsonl` files with their sizes and dates. If there are no past sessions (greenfield brainstorm that lives only in this conversation), note that and go straight to step 5 using only the current conversation.

### 4. Mine the transcripts with a subagent, never inline

The `.jsonl` files are often >1 MB each and will blow the main context. Delegate to a `general-purpose` subagent via the Agent tool. Brief it with:

- The absolute paths of all candidate `.jsonl` files (top-level and `subagents/*.jsonl`), prioritized largest/most-recent first.
- The project name and the one-sentence brainstorm topic.
- A digest of what the current conversation already covered (so it skips duplicates and surfaces only net-new material).
- What to extract, organized for a free-form log: findings/understandings reached, facts and data the user shared, methods worked out, directions chosen and directions rejected with reasons, and open topics still unresolved. Capture the *reasoning*, not just the conclusion.
- What to exclude: solution architecture, conclusions the same session later overturned, chitchat, and anything already in the current-conversation digest.
- Output format: themed Markdown bullets grouped by topic (NOT by session), plus a short list of which session files actually contributed. Follow plain-prose writing (no em dashes, no "crucial/delve/pivotal/showcase", straight quotes, no rule-of-three padding). No Unicode box-drawing characters in any table.

If the project has many transcripts, you may fan out several subagents over disjoint file sets and merge their returns.

### 5. Synthesize and write the brainstorm log

In full capture mode, merge the current-conversation spine (step 2) with the subagent returns (step 4). In checkpoint mode, use only the current-conversation material from step 2. Deduplicate across sources. Where two sessions reached different conclusions on the same point, keep the later one and note the earlier as superseded (don't silently drop it). Organize by theme, not chronology.

Write `BRAINSTORM.md` to the project data dir: `~/.claude/projects/<project_name>/BRAINSTORM.md`. If a `BRAINSTORM.md` already exists, read it first and merge into it rather than clobbering: preserve anything already captured, fold the new material into the existing sections, bump the `Last updated` date. This merge-don't-clobber behavior is what makes repeated checkpoints safe, and it means a later full capture folds everything together without losing prior checkpoints. Use this shape (adapt freely; it is a log, not a rigid form):

```markdown
# BRAINSTORM, <Project or Topic>

**Status:** <In progress, checkpointing | Brainstorm captured, ready for /analyst>
**Last updated:** <YYYY-MM-DD>
**Topic:** <one sentence>
**Sources mined:** current conversation + <N> past sessions (listed in section 8)

## 1. What we're trying to do
The problem in the user's own words, and why now. The motivating context. Keep it WHAT/WHY, not solution.

## 2. Findings and understandings we reached
Themed bullets of the conclusions the brainstorm arrived at. Include the reasoning behind each, not just the verdict.

## 3. Facts and information the user shared
Concrete inputs that future phases must not re-ask for: data shapes, constraints, names, numbers, examples, links, sample records, business rules. Attribute anything that came with a source.

## 4. Methods and approaches worked out
Techniques, rules-of-thumb, sequences, or ways of doing a thing that the session settled on. Keep the reasoning so a later phase knows why this method, not just what it is.

## 5. Directions taken, and directions rejected
- Chosen: <direction>, because <reason>.
- Rejected: <direction>, ruled out because <reason>. (Keep these; they stop the analyst from reopening settled ground.)

## 6. Open topics for the analyst to resolve
The bridge to the next phase. Each is a thread that must be explored or decided before requirements can be written. Phrase as questions or undecided choices, one per bullet. This is the list the analyst works through.

## 7. Deferred action items
Concrete tasks that surfaced but belong later in the process: things to DO, not design questions (those stay in section 6). One per line, with enough context to act on cold. Mark a line `(in TODO)` once it has been handed to the `todo` skill, so a later capture does not add it twice.
- <action item>, <why / context>

## 8. Sources mined
- Current conversation (<date>)
- <session file or title>, <what it contributed>
```

In checkpoint mode, set Status to `In progress, checkpointing`, and the `Sources mined` line can stay as `current conversation` only (the archive pass has not run).

### 6. Hand deferred action items to the todo skill (full capture only)

Read section 7 of `BRAINSTORM.md`. For each action item NOT already marked `(in TODO)`, decide whether it is a real, out-of-scope task that should outlive this brainstorm: a thing to DO, not a design question for the analyst, and not something the current session already finished. If it qualifies, hand it to the `todo` skill rather than editing `TODO.md` yourself. The `todo` skill owns the file shape and the per-project TODO.md plus cross-project index plus memory three-way sync, so going through it keeps one owner for that format. Pass the qualifying items in one batch, each into the bucket the item implies (Active by default). Then annotate each handed-off line in section 7 with `(in TODO)` so a later full capture does not re-add it.

Keep the boundary clean: open design questions stay in section 6 for the analyst, concrete tasks go to TODO. Never put the same item in both. If section 7 is empty or every item is already marked `(in TODO)`, skip this step.

### 7. Report and hand off

In **checkpoint** mode, skip this whole report. Print a single line instead: `Checkpointed N new item(s) to BRAINSTORM.md (<clickable path>).` If any action items were logged to section 7 this round, mention the count in the same line. Then stop.

In **full capture** mode, print a tight summary (5-10 lines):
- Project and topic.
- Where `BRAINSTORM.md` was written (clickable path).
- How many past sessions contributed, and whether the archive pass added much beyond the live conversation (if it added little, say so plainly, it means earlier sessions were already distilled).
- The count of open topics now queued for the analyst.
- The count of deferred action items handed to the `todo` skill (or zero), so it is clear they are now tracked on the project TODO list, not buried in the doc.
- Suggested next step: run `/analyst` in this project; it will read `BRAINSTORM.md` and interview only the open topics instead of starting from zero.

Do not write REQUIREMENTS.md or design anything here. This skill ends at the handoff.

## Notes

- The output is a handoff artifact, not project memory. Do NOT route this content into `MEMORY.md` or the project `CLAUDE.md`, those have their own end-of-session skills (`/save-context`, `/close-session`). `BRAINSTORM.md` is consumed by `/analyst` and can be deleted once REQUIREMENTS.md supersedes it. The one allowed outbound handoff is deferred action items going to the `todo` skill (section 7); that is a deliberate, owned hand-off through another skill, not this skill writing memory or TODO files directly.
- Action items vs open topics, the distinction that keeps the TODO clean: an open topic (section 6) is a decision the analyst must make; an action item (section 7) is a task someone must do. Route decisions to the analyst via the doc, route tasks to the `todo` skill. Do not double-track an item in both places.
- Checkpoint cadence is Claude's responsibility, not a hook's. Claude Code has no per-interval hook, and wiring a PostToolUse hook to checkpoint on every tool call would be too noisy and expensive. The proactive-trigger list above is the mechanism. If the user later wants hard guaranteed autosave on a timer, that is a separate hook project, not part of this skill.
- A checkpoint and a full capture write the SAME file with the SAME merge logic, so checkpoints are never wasted: a later full capture folds them together and adds the archive pass.
- This skill reads transcripts but never deletes them. Leave the archives in place.
- If the user asks to "capture and then spec it," run a full capture to completion, then invoke `/analyst`. Do not blur the two phases into one pass.
