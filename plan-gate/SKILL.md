---
model: inherit
name: plan-gate
description: Verify an approved plan before executing it. The moment you leave plan mode (switch to auto or accept mode), surface every weak spot in the plan and drive each one to fixed or explicitly accepted with the user, reaching shared understanding, before any code is written. Use right after a plan is approved (a hook reminds you), or when the user says "gate this plan", "grill the plan before we start", "verify the plan", or wants a shared-understanding check before execution. Not for stress-testing an early idea (use grill-me); this is the pre-execution gate on an already-approved plan.
disable-model-invocation: false
argument-hint: "[optional path to the approved plan file]"
---

# Plan gate

A checkpoint between approving a plan and executing it. Its job: make sure every weak
spot in the plan is surfaced and either fixed or explicitly accepted by the user, so you
and the user share a complete, gap-free understanding before any change is made. Do not
start implementing until the gate is complete.

## When this runs

- Right after you exit plan mode. A PostToolUse hook on ExitPlanMode injects a reminder.
- Or when the user asks for a plan gate or a verification pass before starting.

## Steps

### 1. Get the approved plan

- If the user passed a path, read that file.
- Otherwise the plan has to be IDENTIFIED, never guessed. `~/.claude/plans/` holds every
  plan from every session, so the newest file there is only your own when nothing else has
  written since, and gating the wrong plan wastes the whole gate while looking correct.
  List the candidates newest first with their times (`ls -lt ~/.claude/plans/ | head -10`)
  and ask which one, with your best guess named as the recommendation. Confirm in one line
  which plan you are gating.
- If neither exists (the plan lives only in the conversation), gate the plan as stated in
  the conversation and say so; the steps below still apply.
- Recall the original goal or request the plan is meant to satisfy. The gate checks the
  plan against that goal, not only against itself.

### 2. Surface the weak spots

Spawn the `plan-auditor` agent (Agent tool, `subagent_type: plan-auditor`) with the plan
file path and the original goal. It reads the plan, checks it against the codebase, and
returns a structured weak-spot report: gaps vs the goal, hidden assumptions, unresolved
decisions, unhandled edge cases, missing failure paths, irreversible steps, verification
gaps, and claims the code contradicts.

If the auditor is not available, do the same analysis inline, but keep the heavy file
reading out of the main thread where you can.

### 3. Drive each weak spot to a resolution, one at a time

This is the interactive core. For each weak spot, in severity order:

1. State it in one or two sentences: the concern and why it matters.
2. Give your recommended resolution.
3. Ask the user to decide. ONE weak spot at a time. Wait for the answer before moving on.
4. Record the outcome as exactly one of:
   - **Fixed** edit the plan file to close the gap.
   - **Accepted** the user explicitly accepts the risk or the choice as-is. Record the
     reason in one line. Accepted is a real, allowed outcome: not every weak spot has to
     be fixed, but every one must be consciously decided.
   - **Routed** the weak spot shows the DESIGN is wrong, not the plan. Fixed cannot
     express this: the plan may be a faithful implementation of an approach that does
     not hold, so driving it to Fixed just polishes the wrong plan. Send it back to the
     design step with the finding, and re-run the gate against the revised plan.

Do not batch the weak spots into one big question. Do not move past a weak spot until it
is Fixed or Accepted. If resolving one changes the plan enough to raise a new weak spot,
add it to the list.

### 4. Confirm shared understanding and release

When every weak spot is Fixed or Accepted:

- Append a short record to the plan file under a `## Plan-gate outcome` heading: the date,
  and each weak spot with its resolution (Fixed, or Accepted plus the reason), so the
  decisions are durable. If there is no plan file, put the same record in your summary
  message instead.
- **Copy every decision that CONSTRAINS CODE into the project CLAUDE.md, with its decision
  number.** A plan is read by SECTION during the build, and the section a builder reads is the
  build slice, not the decisions list at the top. So a number that lives only in the decisions
  list is durable and unreachable: the builder implements the slice, invents whatever the slice
  text left unsaid, writes tests from that same reading, and both agree. Nothing goes red,
  because the only thing that disagrees is a paragraph nobody opened.

  A decision constrains code when an implementer could get it wrong without noticing: a
  threshold, a window, a count, a severity, a cadence, a retention period, an id a token is
  bound to, an enum a state maps onto. Move those. Leave the ones that only describe how the
  work is run (who reviews, where tests run, when to deploy) in the plan.

  Put them where the project already keeps its rules, usually a "Decisions that must not be
  undone silently" section, one line each, each naming the plan and its decision number so the
  full wording is one hop away. The project CLAUDE.md loads at the start of every session in
  that project, which is the whole point: the builder meets the number without having to know
  it exists. **Check the file's own size threshold first**; if it is over, the decisions go to
  the project's satellite and the report says `/split-claude-md` is due.

  **Then prove it with a command, not by reading.** Grep the project file for a distinctive
  phrase of each decision you moved, plus a CONTROL phrase you know is already in the file. A
  zero on the control means the check is broken, not that the file is clean.

  Measured on a real project: a plan's decision 3 fixed the reader feedback rule at "3+
  ratings of 1-2 in 30 days, or a 30-day average below 3.50". The build slice named only the
  two problem codes. The session implemented a 7-day window with a 40% share instead, wrote
  seven tests from that same wrong reading, and committed it with 545 tests green; it was
  caught only because the plan was reopened later for an unrelated reason. Replaying this
  step against that one plan afterwards found ELEVEN more code-constraining rules stranded in
  the decisions list, including the other two thirds of decision 3 and the whole of decision
  10, all still waiting for the slices not yet built. One plan, one gate, twelve live holes.

- Give the user a one-screen summary: N weak spots, X fixed, Y accepted, the net
  changes to the plan, and which decisions were copied into the project CLAUDE.md.
- State plainly that the gate is complete and you are about to execute the (possibly
  updated) plan. Then proceed.

## Rules

- The gate is a checkpoint, not a veto. The user can accept any weak spot, or tell you to
  skip the gate entirely. Honor that, but make the skip explicit.
- One question at a time, with a recommended answer for each. Resolve it, then move on.
- "Accepted" needs the user's explicit say-so, never your assumption. If the user has not
  answered, the weak spot is not resolved.
- This is the pre-execution gate on an already-approved plan. To stress-test a rough idea
  or an early document before a plan exists, use grill-me instead.
- Keep it tight. Surface real weak spots, not manufactured ones. If the plan is solid, say
  so, resolve the few real items, and release quickly.
