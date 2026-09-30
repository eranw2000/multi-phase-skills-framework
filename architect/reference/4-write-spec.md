**Precondition (hard gate):** Do not write SPEC.md until BOTH of these are true:

1. Every area in step 3 has a concrete choice or a flagged Open Question. The eleven areas: module boundaries, data model, control flow, integration points, NFR satisfaction, observability, security and privacy, deployment and operations, migration and rollout, cross-cutting concerns, risks.
2. The coverage matrix (step 3.5) accounts for every FR/NFR/C from REQUIREMENTS.md.

If the user pushes to skip ("just write it"), explain that a thin SPEC.md silently strands requirements and produces TDD tests for the wrong system. Offer a fast path: for each unvisited area, ask one highest-leverage question. "Defer to developer" or "flag as OQ" are valid answers, but record the answer. Never silently skip.

**Second precondition (hard gate): the single-slot check.** `SPEC.md` at the project root is a
single slot. Every initiative in the repo writes to that one path, so a second initiative
destroys the first one's specification. No test can see the loss, because a specification has no
runtime behavior to break.

Resolve your target path first. If a `docs/*/SPEC.md` already exists whose `Initiative`
field names the initiative you are writing for, THAT file is your target, and the copy at
the usual path is not yours to touch. Otherwise your target is the usual path. Then, on
the target you resolved:

1. Check whether the target path already exists. If it does not, write normally and ask
   nothing. A path that holds no file yet must never produce a question here.
2. If it exists, read its `Initiative` field.
3. If that field names the initiative you are working on, proceed as today.
4. If it names a different initiative, or the field is absent, STOP and ask the user.
   Name the initiative that owns the file on disk, name the one you were about to write
   for, and offer the alternative in the same breath: write to
   `docs/<initiative>/SPEC.md` instead and leave the existing file untouched.
5. Never overwrite on your own judgement, and never merge two initiatives into one file.

An absent `Initiative` field counts as a different initiative, not as a free slot. Every
spec file written before this rule lacks the field, so reading absence as permission
would make the check inert exactly where the risk is highest.

```markdown
# SPEC, <project>

**Initiative:** <the one initiative this file describes>
**Governing plan:** <absolute path to the plan or decision record this file implements, or the words "this file and REQUIREMENTS.md beside it" when there is no separate plan>
**State as of <YYYY-MM-DD>:** <In flight | Delivered | Abandoned>, with the evidence, for example which issues are still open.
**Do not overwrite this file for a different initiative.** A later initiative writes its own under `docs/<initiative>/SPEC.md`.

**Status:** Draft for OpenSpec proposal
**Last updated:** <YYYY-MM-DD>
**Requirements source:** REQUIREMENTS.md

## 1. Overview
Two or three paragraphs. What is being built, the shape of the design, why this shape.

## 2. Architecture
Reference `architecture.drawio` (prefer draw.io over ASCII or Mermaid). Include one paragraph per component below the reference.

## 3. Module Inventory
| Module | Responsibility | Public interface | State |
| --- | --- | --- | --- |

## 4. Data Model
Persistent entities, relationships, source of truth.

## 5. Key Decisions
- D-1: <decision>. Anchors to: <requirement IDs>. Alternatives considered: <list>. Why this: <reason>.

## 6. NFR Satisfaction
| NFR ID | Mechanism |
| --- | --- |

## 7. Risks and Mitigations
| Risk | Likelihood | Impact | Mitigation |
| --- | --- | --- | --- |

## 8. Open Questions
1. OQ-1:

## 9. Rollout
Order of deploy steps, feature flags, backfills, verification.

## 10. Coverage Matrix
Every requirement from REQUIREMENTS.md, accounted for. Zero silent drops.

| Requirement ID | Status | Anchor |
| --- | --- | --- |
| FR-1 | Satisfied | D-3 |
| FR-2 | Deferred | OQ-1 |
| NFR-PERF-1 | Satisfied | D-5 |
| C-1 | Out of scope | User confirmed YYYY-MM-DD: <reason> |
```
