---
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
- Otherwise read the most recently modified file in `~/.claude/plans/` (the plan you just
  got approved). Confirm in one line which plan you are gating.
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

Do not batch the weak spots into one big question. Do not move past a weak spot until it
is Fixed or Accepted. If resolving one changes the plan enough to raise a new weak spot,
add it to the list.

### 4. Confirm shared understanding and release

When every weak spot is Fixed or Accepted:

- Append a short record to the plan file under a `## Plan-gate outcome` heading: the date,
  and each weak spot with its resolution (Fixed, or Accepted plus the reason), so the
  decisions are durable. If there is no plan file, put the same record in your summary
  message instead.
- Give the user a one-screen summary: N weak spots, X fixed, Y accepted, and the net
  changes to the plan.
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
