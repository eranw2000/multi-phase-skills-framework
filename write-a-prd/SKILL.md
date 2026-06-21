---
name: write-a-prd
description: Create a PRD for a single, well-bounded feature through a user interview, codebase exploration, and a deep-module design pass, then file it as one issue ready to implement. Use this whenever the user wants to write a PRD, spec out a feature, plan a new feature, or turn a feature idea into an actionable ticket, even if they do not say "PRD" by name. This skill produces only a PRD; it never creates a REQUIREMENTS.md. Defer to /analyst (then /architect) when the work spans multiple features, the scope is still unclear, the project needs numbered FR/NFR IDs for sign-off or compliance, or the need itself is unvalidated. To break an existing plan or spec into many issues, use /prd-to-issues instead.
argument-hint: "[optional one-line feature description]"
---

# Write a PRD

<!-- Based on the Matt Pocock skills set (https://github.com/mattpocock). -->

Write a PRD for a single feature, then file it as one issue a developer can pick up. This is the lightweight path: one interview, one document, one issue. It folds a small requirements pass and a small design pass into a single artifact, which is why it suits a feature you can already see the shape of.

Reach for `/analyst` (then `/architect`) instead when the work is bigger than one feature, the scope is still fuzzy, you need numbered FR/NFR IDs for client sign-off or compliance, or the "should we even build this" question is still open. Those cases earn the heavier three-document chain (REQUIREMENTS.md, SPEC.md, sliced issues). This skill deliberately does not produce a REQUIREMENTS.md; if you find yourself needing one, that is the signal to switch to `/analyst`.

The single deliverable is a PRD, filed as one issue on the project's tracker (GitHub issues, Linear, Jira, etc.). If the project has no tracker, save it as `PRD.md` at the repo root (or the project data dir when there is no repo) and note in the doc that it should move to a tracker once one exists.

## Core disciplines (top 3)

Three things this skill cares about most. Everything below amplifies these three.

1. **Shared understanding before writing.** Interview the user until you both agree on the problem and the solution, walking the decision tree one branch at a time. The PRD records a conclusion you reached together, not a first draft you guessed at. A misheard requirement here is cheap to fix; the same mistake found at implementation or user-verification time is expensive.

2. **Deep modules over shallow ones.** Sketch the modules to build or change, and look hard for deep modules: a lot of functionality behind a simple interface that rarely changes and can be tested in isolation. A shallow module exposes almost as much interface as it has behavior, so it earns its keep less and tends to leak its internals into everything that touches it.

3. **Testable user stories plus explicit test and scope boundaries.** Write user stories concrete enough to test, and fill in the Testing Decisions and Out of Scope sections rather than leaving them blank. Without them, "is it done?" has no answer and scope creeps because no line was ever drawn.

## Process

Skip a step when you genuinely do not need it, but do not skip the step-6 hard gate.

### 1. Gather the problem

Ask the user for a long, detailed description of the problem they want to solve and any ideas they have for a solution. Listen for the problem in their own words before any solution talk. If a one-line description came in as an argument, treat it as the starting point and expand it with the user.

### 2. Explore the codebase

Explore the repo to verify the user's assertions and understand the current state of the code. Use the project's existing vocabulary in the PRD so it reads as native to the codebase. Read prior art and any decision records in the area you are touching. Answer from the code whatever the code can answer instead of asking the user.

### 3. Interview to shared understanding

Interview the user relentlessly about every aspect of the plan until you both share the same understanding. Walk each branch of the decision tree, resolving the dependencies between decisions one at a time. Ask one question at a time. For a question the codebase can answer, go read it instead of asking.

### 4. Design the modules

Sketch the major modules you will build or modify to complete the implementation. Actively look for deep modules to extract (see discipline #2). Check with the user that the modules match their expectations before writing anything down, because a wrong module boundary is the most expensive thing to discover after implementation starts.

### 5. Agree on test scope

Check with the user which modules they want tests for, and what a good test looks like here (test external behavior, not implementation details). Note prior art: similar kinds of tests already in the codebase, so the developer has a pattern to follow.

### 6. Write the PRD and file it

**Precondition (hard gate):** do not file the PRD until both are true:

1. The interview reached shared understanding. The problem, the solution, and the module sketch were each confirmed by the user (steps 3 and 4). "Looks fine, keep going" counts; silence does not.
2. The destination is known. The project's tracker, or a file path if there is no tracker.

Write the PRD with the template below, then file it as a single issue on the tracker (or save the file). You may skip a template section when it genuinely does not apply, but keep Testing Decisions and Out of Scope; they are where this skill earns its keep.

<prd-template>

## Problem Statement
The problem that the user is facing, from the user's perspective.

## Solution
The solution to the problem, from the user's perspective.

## User Stories

A LONG, numbered list of user stories. Each user story should be in the format of:

1. As an <actor>, I want a <feature>, so that <benefit>

<user-story-example>
1. As a mobile bank customer, I want to see the balance on my accounts, so that I can make better informed decisions about my spending
</user-story-example>

This list of user stories should be extremely extensive and cover all aspects of the feature.

## Implementation Decisions

A list of implementation decisions that were made. This can include:

- The modules that will be built/modified
- The interfaces of those modules that will be modified
- Technical clarifications from the developer
- Architectural decisions
- Schema changes
- API contracts
- Specific interactions

Do NOT include specific file paths or code snippets. They may end up being outdated very quickly.

Exception: if a prototype produced a snippet that encodes a decision more precisely than prose can (state machine, reducer, schema, type shape), inline it within the relevant decision and note briefly that it came from a prototype. Trim to the decision-rich parts, not a working demo, just the important bits.

## Testing Decisions

A list of testing decisions that were made. Include:

- A description of what makes a good test (only test external behavior, not implementation details)
- Which modules will be tested
- Prior art for the tests (i.e. similar types of tests in the codebase)

## Out of Scope

A description of the things that are out of scope for this PRD.

## Further Notes

Any further notes about the feature.

</prd-template>

## Output checklist

Before declaring the PRD done, verify:

- [ ] Problem and solution are stated from the user's perspective, not as implementation.
- [ ] User stories are extensive and each one is in the "As an <actor>, I want a <feature>, so that <benefit>" form.
- [ ] Implementation Decisions capture modules, interfaces, and schema/API contracts. No specific file paths or code snippets (the prototype-snippet exception aside).
- [ ] Testing Decisions name which modules are tested and what a good test is here.
- [ ] Out of Scope is explicit, not implied by omission.
- [ ] The user confirmed the module sketch before the PRD was filed.
- [ ] The PRD was filed where the user expects it (a tracker issue, or `PRD.md`).
- [ ] No REQUIREMENTS.md was produced. If one was needed, the work should have gone to /analyst.
- [ ] Plain prose: no em dashes, no marketing adjectives, no Unicode box-drawing characters in tables.

## Handoff

When the PRD is filed, tell the user:

- Where it landed (issue URL or file path).
- The suggested next step: slice it into tracer-bullet vertical-slice issues with `/prd-to-issues`, or implement it directly with `/tdd` if it is small enough to be a single slice.
