<!-- Based on the domain-modeling skill by Matt Pocock (https://github.com/mattpocock/skills/tree/main/skills/engineering/domain-modeling). -->

# ADR format

ADRs (Architecture Decision Records) live in `docs/adr/`, numbered sequentially (`0001-slug.md`, `0002-slug.md`; scan for the highest number and increment). Create the directory lazily, on the first ADR.

Template (a single paragraph is a complete ADR; the value is recording that a decision was made and why):

```md
# {Short title of the decision}

{1-3 sentences: the context, the decision, and why.}
```

Optional sections, only when they genuinely add value: a `Status` line (proposed / accepted / deprecated / superseded by ADR-NNNN), Considered Options, Consequences.

Offer an ADR only when all three hold:

1. **Hard to reverse**: changing your mind later has real cost.
2. **Surprising without context**: a future reader would wonder why it was done this way.
3. **A real trade-off**: genuine alternatives existed and one was chosen for specific reasons.

What typically qualifies: architectural shape, integration patterns between contexts, technology choices that carry lock-in, boundary and ownership decisions, deliberate deviations from the obvious path, constraints not visible in the code, and rejected alternatives when the rejection is non-obvious.
