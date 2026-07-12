---
model: fable
name: prd-to-issues
description: Break a plan, spec, or PRD into independently-grabbable issues on the project issue tracker using tracer-bullet vertical slices. Use when user wants to convert a plan into issues, create implementation tickets, or break down work into issues.
---

# To Issues

<!-- Based on the Matt Pocock skills set (https://github.com/mattpocock). -->

Break a plan into independently-grabbable issues using vertical slices (tracer bullets).

The issue tracker and triage-label vocabulary should have been provided to you; if not, ask the user which tracker the project uses (GitHub issues, Linear, Jira, etc.) and what label marks an issue as ready for an AFK agent. If the project has no repo or tracker yet (greenfield), create the repo under the team's GitHub org (or whatever remote the user names) first; issues need a home before slicing.

## Core disciplines (top 3)

Three things this skill cares about most. Everything below is amplification of these three.

1. **Tracer-bullet vertical slicing** (see step 3 + vertical-slice-rules). Every issue is a thin slice through ALL integration layers (schema, API, UI, tests) end-to-end, NOT a horizontal slice of one layer. The tracer-bullet test: if you cannot demo or deploy this slice on its own behind a feature flag, it is not a vertical slice. Re-slice.

2. **Walking skeleton first** (see vertical-slice-rules + template "Walking skeleton" field). The first slice must be the smallest end-to-end thing that proves the architecture connects: deploy pipeline + auth + one trivial endpoint + one trivial UI element + one trivial test, all wired together. Almost nothing user-visible by design. Its job is to de-risk every later slice by removing "does the plumbing work?" from each one.

3. **Source-doc traceability + precondition gate (paired)** (see issue-template `Source` + `Requirements covered` fields, plus step 5 hard gate). Every issue points back to the spec/PRD/requirements doc it was sliced from, by file path or URL, with the specific FR-N / NFR-X-N / D-N / user story IDs it satisfies. The gate refuses to publish until the source is named, the user has explicitly approved the breakdown, AND at least one slice is AFK with no blockers.

Failure modes these three prevent:

- Without #1 → **big-bang integration at the end** (horizontal slicing produces "API layer done, UI layer done, now wire them together for six weeks" — integration bugs all surface at once when they're most expensive)
- Without #2 → **every later slice carries plumbing risk** (no proof that deploy / auth / data path / test loop actually works; you find out three weeks in when something tries to ship)
- Without #3 → **orphan issues, can't audit later** (issues exist disconnected from the requirement that birthed them; a later review has nothing to anchor against; six weeks in, "why are we building this?" has no answer)

If you find yourself short on tokens or attention and have to skip something, skip detail in the supporting fields (Size signal, HITL/AFK label correctness, dependency-order publishing) before skipping anything from these three.

## Process

### 1. Gather context

Work from whatever is already in the conversation context. If the user passes an issue reference (issue number, URL, or path) as an argument, fetch it from the issue tracker and read its full body and comments.

### 2. Explore the codebase (optional)

If you have not already explored the codebase, do so to understand the current state of the code. Issue titles and descriptions should use the project's domain glossary vocabulary, and respect ADRs in the area you're touching.

### 3. Draft vertical slices

Break the plan into **tracer bullet** issues. Each issue is a thin vertical slice that cuts through ALL integration layers end-to-end, NOT a horizontal slice of one layer.

Slices may be 'HITL' or 'AFK'. HITL slices require human interaction, such as an architectural decision or a design review. AFK slices can be implemented and merged without human interaction. Prefer AFK over HITL where possible.

<vertical-slice-rules>
- Each slice delivers a narrow but COMPLETE path through every layer (schema, API, UI, tests)
- A completed slice is demoable or verifiable on its own
- Prefer many thin slices over few thick ones
- The FIRST slice must be a walking skeleton: the smallest end-to-end thing that proves the architecture connects. Deploy pipeline + auth + one trivial endpoint + one trivial UI element + one trivial test, all wired together. Does almost nothing user-visible by design. Its job is to de-risk every later slice by removing "does the plumbing work?" from each one.
- Tracer-bullet test: if you cannot demo or deploy this slice on its own behind a feature flag, it is not a vertical slice. Re-slice.
</vertical-slice-rules>

### 4. Quiz the user

Present the proposed breakdown as a numbered list. For each slice, show:

- **Title**: short descriptive name
- **Type**: HITL / AFK
- **Size**: S / M / L (rough load signal, not an estimate; S ≈ one focused session, M ≈ a day, L ≈ multi-day and probably should be split)
- **Walking skeleton**: Yes on slice 1 only, No on the rest
- **Blocked by**: which other slices (if any) must complete first
- **Requirements covered**: FR-N / NFR-X-N / D-N IDs from REQUIREMENTS.md or SPEC.md when those exist, or user story IDs from a PRD, or a brief plain-text description when the source has no IDs

Ask the user:

- Does the granularity feel right? (too coarse / too fine)
- Are the dependency relationships correct?
- Should any slices be merged or split further?
- Are the correct slices marked as HITL and AFK?

Iterate until the user approves the breakdown.

### 5. Publish the issues to the issue tracker

**Precondition (hard gate):** Do not publish until all three are true:

1. The source plan is identified by name. Specify the file path (`SPEC.md`, `REQUIREMENTS.md`, `PRD.md`) or the source issue URL. "Whatever was in conversation" is not enough — the issues must point back to a real artifact so a later review can anchor.
2. The user explicitly approved the step-4 breakdown. "Looks fine, keep going" counts; silence does not.
3. At least one slice is AFK with no blockers. If every slice is HITL or blocked, the breakdown isn't ready for an AFK agent. Tell the user why and re-slice.

If any precondition fails, return to step 4 and resolve before publishing.

For each approved slice, publish a new issue to the issue tracker. Use the issue body template below. These issues are considered ready for AFK agents, so publish them with the correct triage label unless instructed otherwise.

Publish issues in dependency order (blockers first) so you can reference real issue identifiers in the "Blocked by" field.

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

Yes / No. Yes only on the first slice; the smallest end-to-end thing that proves the architecture connects.

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

### 6. Handoff to Developer

Tell the user:
- The list of published issue IDs and titles, in dependency order.
- Which slice is the walking skeleton (always slice 1).
- Any issues marked HITL and what decision each one needs.
- The suggested next step: invoke `/tdd` against the walking-skeleton issue first. Once it merges, the next AFK slice unblocks.

## Output checklist

Before declaring the breakdown done, verify:

- [ ] Source plan is named (file path or doc URL), not "whatever was in conversation."
- [ ] User explicitly approved the step-4 breakdown before any publishing happened.
- [ ] First slice is the walking skeleton (Yes in the template). Every later slice is No.
- [ ] Every slice passes the tracer-bullet test: could be demoed or deployed behind a feature flag on its own.
- [ ] Every slice has a Size (S/M/L). No L slices remain (they should have been split).
- [ ] Every acceptance criterion describes user-visible or system-observable behavior, not implementation choices.
- [ ] Every requirement (FR-N / NFR-X-N / D-N / user story) from the source plan is covered by at least one issue. Zero silent drops.
- [ ] Dependency graph is acyclic. Every "Blocked by" references a real issue ID published earlier in dependency order.
- [ ] At least one AFK issue has no blockers (something is grabbable now).
- [ ] AFK preference applied: no slice is HITL where AFK would have worked.
