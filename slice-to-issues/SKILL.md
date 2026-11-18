---
model: inherit
name: slice-to-issues
description: Break a plan, spec, or PRD into independently-grabbable issues on the project issue tracker using tracer-bullet vertical slices. Use when user wants to convert a plan into issues, create implementation tickets, or break down work into issues.
---

# Slice to issues

<!-- Based on the Matt Pocock skills set (https://github.com/mattpocock). -->

Break a plan into independently-grabbable issues using vertical slices (tracer bullets).

The issue tracker and triage-label vocabulary should have been provided to you; if not, ask the user which tracker the project uses (GitHub issues, Linear, Jira, etc.) and what label marks an issue as ready for an AFK agent. If the answer is that the project has no tracker yet, do not create one: write the slices to `docs/<initiative>/SLICES.md` instead (step 6 says how), and note in the file that they move to a tracker once one exists.

## Core disciplines (top 3)

Three things this skill cares about most. Everything below is amplification of these three.

1. **Tracer-bullet vertical slicing** (see step 4 + vertical-slice-rules). Every issue is a thin slice through ALL integration layers (schema, API, UI, tests) end-to-end, NOT a horizontal slice of one layer. The tracer-bullet test: if you cannot demo or deploy this slice on its own behind a feature flag, it is not a vertical slice. Re-slice.

2. **Walking skeleton first, when the plumbing is new** (see vertical-slice-rules + template "Walking skeleton" field). When the work needs a path through the system that has never run end to end (a new app, service, deploy target, data store, or the first screen of a new area), the first slice is a walking skeleton: the smallest end-to-end thing that proves that path connects, such as deploy pipeline + auth + one trivial endpoint + one trivial UI element + one trivial test. Almost nothing user-visible by design. Its job is to de-risk every later slice by removing "does the plumbing work?" from each one. When the feature rides on plumbing that already ships, a skeleton proves nothing new: slice 1 is the thinnest real feature slice instead. Say which case applies, and why, when you show the breakdown.

3. **Source-doc traceability + precondition gate (paired)** (see issue-template `Source` + `Requirements covered` fields, the step-5 coverage list, plus the step-6 hard gate). Every issue points back to the spec/PRD/requirements doc it was sliced from, by file path or URL, with the specific FR-N / NFR-X-N / D-N / user story IDs it satisfies. The gate refuses to publish until the source is named, every requirement in it maps to a slice (or the user put it out of scope), the user has explicitly approved the breakdown, AND at least one slice is AFK with no blockers.

Failure modes these three prevent:

- Without #1 → **big-bang integration at the end** (horizontal slicing leaves all the wiring, and all its bugs, for the end, when they cost most)
- Without #2, on new plumbing → **every later slice carries plumbing risk** (no proof that deploy / auth / data path / test loop actually works; you find out three weeks in when something tries to ship)
- Without #3 → **orphan issues, can't audit later** (issues exist disconnected from the requirement that birthed them; a later review has nothing to anchor against; six weeks in, "why are we building this?" has no answer)

Short on attention? Skip detail in the supporting fields (Size, HITL/AFK labels, publish order) before anything from these three.

## Process

### 1. Gather context

Work from whatever is already in the conversation context. If the user passes an issue reference (issue number, URL, or path) as an argument, fetch it from the issue tracker and read its full body and comments.

### 2. Find the spec that belongs to your initiative

A repo hosts more than one initiative over its life. The first writes `REQUIREMENTS.md`
and `SPEC.md` at the repo root, and a later one writes its own under
`docs/<initiative>/`. So the copy at the root is not always the one you want, and
grounding on the wrong initiative's spec produces work that is internally consistent
and aimed at the wrong system, which review does not catch.

Say which initiative this work is for, then resolve the file instead of assuming the
root copy:

1. List the candidates: the repo root copy, every `docs/*/` copy, and any other
   location this skill already tells you to check.
2. Read the `Initiative` field of each. That field decides, never the directory name,
   which is a slug somebody chose and can be stale or wrong.
3. Exactly one names your initiative: use it, and say which path you used.
4. None names it: STOP and tell the user what you found and where. Do not fall back to
   the root copy.
5. More than one names it: STOP and name every path. Two files claiming one initiative
   is a thing to report, not to settle by picking one.
6. A candidate carries no `Initiative` field: say so. Where it is the only candidate you
   may use it, and you must say you read a spec with no recorded owner.

When the user hands you an explicit path, use that path. Check its `Initiative` field
the same way, and on a mismatch stop and say whether a file for your initiative sits
somewhere else.

Slices cut from the wrong spec become issues that point back to it, so the wrong source travels into the tracker and outlives the mistake.

### 3. Explore the codebase (optional)

If you have not explored the codebase yet, do so now. Issue titles and descriptions use the project's domain vocabulary and respect ADRs in the area you're touching.

### 4. Draft vertical slices

Break the plan into **tracer bullet** issues. Each issue is a thin vertical slice that cuts through ALL integration layers end-to-end, NOT a horizontal slice of one layer.

Slices may be 'HITL' or 'AFK'. HITL slices require human interaction, such as an architectural decision or a design review. AFK slices can be implemented and merged without human interaction. Prefer AFK over HITL where possible.

<vertical-slice-rules>
- Each slice delivers a narrow but COMPLETE path through every layer (schema, API, UI, tests)
- A completed slice is demoable or verifiable on its own
- Prefer many thin slices over few thick ones
- When the plumbing is new, the FIRST slice is a walking skeleton (core discipline #2 says what goes in it). When the feature rides on plumbing that already ships, there is no skeleton and slice 1 is the thinnest real feature slice.
- Tracer-bullet test: if you cannot demo or deploy this slice on its own behind a feature flag, it is not a vertical slice. Re-slice.
</vertical-slice-rules>

### 5. Quiz the user

Present the proposed breakdown as a numbered list. For each slice, show:

- **Title**: short descriptive name
- **Type**: HITL / AFK
- **Size**: S / M / L (rough load signal, not an estimate; S ≈ one focused session, M ≈ a day, L ≈ multi-day and probably should be split)
- **Walking skeleton**: Yes on slice 1 only when the plumbing is new, No everywhere else. Say in one line which case applies and why.
- **Blocked by**: which other slices (if any) must complete first
- **Requirements covered**: FR-N / NFR-X-N / D-N IDs from REQUIREMENTS.md or SPEC.md when those exist, or user story IDs from a PRD, or a brief plain-text description when the source has no IDs

Then show the **coverage list**, built from the source and not from the slices: every requirement ID (or user story) in the source, one per line, with the slices that cover it, for example `FR-3 -> slices 2, 4`. A requirement no slice covers is marked `NOT COVERED`. Each one must end as a new or widened slice, or as out of scope because the user said so. Use a plain list, not a table.

Ask the user:

- Does the granularity feel right? (too coarse / too fine)
- Are the dependency relationships correct?
- Should any slices be merged or split further?
- Are the correct slices marked as HITL and AFK?
- Is anything marked NOT COVERED out of scope, or does it need a slice?

Iterate until the user approves the breakdown.

### 6. Publish the issues to the issue tracker

**Precondition (hard gate):** Do not publish until all four are true:

1. The source plan is identified by name. Specify the file path (`SPEC.md`, `REQUIREMENTS.md`, `PRD.md`) or the source issue URL. "Whatever was in conversation" is not enough: the issues must point back to a real artifact so a later review can anchor.
2. The user explicitly approved the step-5 breakdown. "Looks fine, keep going" counts; silence does not.
3. At least one slice is AFK with no blockers. If every slice is HITL or blocked, the breakdown isn't ready for an AFK agent. Tell the user why and re-slice.
4. The step-5 coverage list has no `NOT COVERED` line left: each one became a slice, or the user put it out of scope.

If any precondition fails, return to step 5 and resolve before publishing.

For each approved slice, publish a new issue to the issue tracker. Use the issue body template below. These issues are considered ready for AFK agents, so publish them with the correct triage label unless instructed otherwise.

Publish issues in dependency order (blockers first) so you can reference real issue identifiers in the "Blocked by" field.

**No tracker:** write every slice into one file, `docs/<initiative>/SLICES.md`, instead of issues. Start it with the same four header lines a spec file carries (`Initiative`, `Governing plan`, a dated `State`, and "Do not overwrite this file for a different initiative"), then the coverage list, then one `## S<n>: <title>` section per slice in dependency order, using the template below. "Blocked by" names S-numbers. If the file already exists, read its `Initiative` field first: the same initiative means update it in place; a different or missing one means STOP and ask, and never overwrite.

<issue-template>
## Parent

A reference to the parent issue on the issue tracker (if the source was an existing issue, otherwise omit this section).

## Source

The plan, spec, or PRD this slice was sliced from. Examples: `SPEC.md`, `REQUIREMENTS.md`, `PRD.md`, or a doc URL. Required so a later review can anchor back.

## Requirements covered

The specific IDs this slice satisfies. Examples:
- `FR-3, FR-7, NFR-PERF-1` (when source is REQUIREMENTS.md)
- `D-2, D-5` (when source is SPEC.md design decisions)
- User story IDs (when source is a PRD with stories)
- Brief plain-text description (when source has no IDs)

## Size

S / M / L. Rough load signal, not an estimate. S ≈ one focused session, M ≈ a day, L ≈ multi-day (should have been split before publishing).

## Walking skeleton

Yes / No. Yes only on the first slice, and only when the plumbing is new: the smallest end-to-end thing that proves the new path connects.

## What to build

A concise description of this vertical slice. Describe the end-to-end behavior, not layer-by-layer implementation.

Avoid specific file paths or code snippets — they go stale fast. Exception: if a prototype produced a snippet that encodes a decision more precisely than prose can (state machine, reducer, schema, type shape), inline it here and note briefly that it came from a prototype. Trim to the decision-rich parts — not a working demo, just the important bits.

## Acceptance criteria

Each criterion describes user-visible or system-observable behavior, not implementation choices. These become the tests in TDD.

- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

## Blocked by

- A reference to the blocking ticket (if any)

Or "None - can start immediately" if no blockers.

</issue-template>

Do NOT close or modify any parent issue.

### 7. Handoff to Developer

Tell the user:
- The list of published issue IDs (or S-numbers in `SLICES.md`) and titles, in dependency order.
- Whether slice 1 is a walking skeleton, and why or why not.
- Any issues marked HITL and what decision each one needs.
- Anything the user put out of scope from the coverage list.
- The suggested next step: invoke `/tdd` against slice 1 first. Once it merges, the next AFK slice unblocks.

## Output checklist

Before declaring the breakdown done, verify:

- [ ] Source plan is named (file path or doc URL), not "whatever was in conversation."
- [ ] User explicitly approved the step-5 breakdown before any publishing happened.
- [ ] Slice 1 is a walking skeleton only when the plumbing is new, and the breakdown said which case applied and why. Every later slice is No.
- [ ] Every slice passes the tracer-bullet test: could be demoed or deployed behind a feature flag on its own.
- [ ] Every slice has a Size (S/M/L). No L slices remain (they should have been split).
- [ ] Every acceptance criterion describes user-visible or system-observable behavior, not implementation choices.
- [ ] The coverage list was shown before publishing, built from the source. Every requirement (FR-N / NFR-X-N / D-N / user story) is covered by at least one issue or was put out of scope by the user. Zero silent drops.
- [ ] With no tracker, the slices went to `docs/<initiative>/SLICES.md` and no repo or tracker was created.
- [ ] Dependency graph is acyclic. Every "Blocked by" references a real issue ID published earlier in dependency order, or, in `SLICES.md`, an S-section written above it.
- [ ] At least one AFK issue has no blockers (something is grabbable now).
- [ ] AFK preference applied: no slice is HITL where AFK would have worked.
