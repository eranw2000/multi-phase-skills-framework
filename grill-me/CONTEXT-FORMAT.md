<!-- Based on the domain-modeling skill by Matt Pocock (https://github.com/mattpocock/skills/tree/main/skills/engineering/domain-modeling). -->

# CONTEXT.md format

One glossary entry per canonical term:

```md
# {Context name}

{One or two sentences: what this context is and why it exists.}

## Language

**Invoice**:
A request for payment sent to a customer after delivery.
_Avoid_: Bill, payment request
```

Rules:

- Pick one winner per concept; list the rejected synonyms under `_Avoid_`.
- Definitions are one or two sentences and say what the term IS, not what it does.
- Only concepts specific to this project belong. General programming vocabulary (timeouts, retries, error types) stays out, even when the project uses it heavily.
- Group terms under subheadings only when natural clusters emerge; a flat list is fine.

Multi-context repos: a root `CONTEXT-MAP.md` lists the contexts, where each context's `CONTEXT.md` lives, and how the contexts relate. If only a root `CONTEXT.md` exists, the repo is single-context. Create files lazily: nothing exists until the first term is resolved.
