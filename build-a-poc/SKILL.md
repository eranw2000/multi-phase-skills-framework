---
name: build-a-poc
description: Build a throwaway prototype that answers a stated validation question before the real implementation starts, then name what it could not answer. Decide during planning whether one is warranted, using the gate below. Use when the plan targets a stack that is slow or expensive to iterate in (corporate .NET, a private package feed, deploy-to-test, an environment you cannot run locally), when the requirement is contested or can only be settled by seeing it run, or when a load-bearing premise is unmeasured. Also fires on "build a POC", "prototype this first", "mock it up before we build it", "validate the UX before implementing", "should we prototype this". Not for bug fixes, refactors, or well-understood work where the real stack iterates just as fast. A POC is not a first draft of the product.
disable-model-invocation: false
argument-hint: "[optional what to validate, or a path to the plan or spec]"
---

# Build a POC

A POC answers a question you cannot answer by reading, arguing, or guessing. It is not a
first version of the product, and it is not a head start on the implementation. It exists
to make one uncertainty cheap to settle, and its most valuable output is often the list of
things it turned out it could NOT settle.

Deliberately no `model:` frontmatter pin. This skill straddles the planning/implementation
boundary (the gate and the design are judgment work, the build is implementation), the same
shape as `pause-after-planning`, which carries no pin for the same reason. Do not add one
during a routing audit.

## Phase 0. The gate. Decide during planning, and say the decision out loud

Run this while the plan is being formed, before the plan commits to building anything.

A POC is warranted when two or more of these hold:

1. The question can only be settled by seeing it or running it. Layout, interaction,
   workflow feel, "is this actually the screen the user wants", "does this flow survive
   a real user's path through it".
2. The target stack is slow or expensive to iterate in. A private package feed you cannot
   restore locally, a source server you cannot reach, a database only reachable on the corp
   network, a change that needs a deploy before anyone can look at it.
3. The requirement is contested or ambiguous, or two stakeholders hold different baselines
   and nobody has reconciled them.
4. A load-bearing premise is unmeasured and the plan's SCOPE depends on it. Name that
   assumption and test it cheaply before committing build time to it; a POC is one
   cheap way to do that.
5. The POC costs a small fraction of what being wrong in the real stack costs.

A POC is NOT warranted when:

- The real stack iterates as fast as any prototype would. Then just build the real thing
  behind a flag and look at it.
- The answer is available by reading the code or asking the person who owns the definition.
  Price that first, every time. It is free and it is faster.
- The work is a bug fix, a refactor, or a feature whose shape nobody disputes.
- The uncertainty is about the CORRECTNESS OF RULES rather than about experience. A
  prototype fed data you invented will confirm whatever you already believe. Rules get
  settled against the definition owner and against real data, not against a prototype.

Say the decision either way, in one line, in the plan. "No POC, the requirement is settled
and the real stack runs locally" is a real output and it stops the question from being
re-litigated later.

## Phase 1. Write the validation questions down before building anything

This is the single discipline that keeps a POC from turning into a second implementation.

For each question, write four things:

- What is unknown.
- What evidence would answer it.
- Who judges the answer (a name, not "the team").
- What result would refute the current plan.

Cap it at one to three questions. Everything else is explicitly out of scope and goes in
the "what this is not" list in Phase 3. If you cannot state a question, you do not need a
POC, you need to scope the work.

## Phase 2. Pick the cheapest medium that answers the question

A ladder, cheapest rung first. Take the lowest rung that actually answers the question, and
state which rung you picked and why.

1. Ask the owner, or read the code. Costs nothing. Say that you tried it.
2. A diagram, when the question is about structure, flow, or who talks to whom.
3. A static mock (HTML, a screenshot, a slide) when the question is purely about layout or
   copy.
4. A runnable prototype in a fast stack (Django, Flask, Streamlit, static HTML plus JS)
   when the question is about interaction, workflow, or "what does this feel like with real
   volume in it".
5. A tracer bullet in the REAL stack when the question is about the real stack. Auth,
   a stored procedure, a framework constraint, a serialization format. A prototype in a
   different stack cannot answer a question about this one, and pretending otherwise is how
   a POC produces a confident wrong answer.

## Phase 3. Build it thin, and label what it is not

- It lives in its own repo or its own directory. Never inside the production tree.
- Before writing code, write "what this POC is NOT" at the top of its README or CLAUDE.md.
  That list is what stops scope creep two days later.
- Skip auth, skip persistence, skip error handling, skip the admin screens, unless one of
  those IS the question.
- Put the behavior logic in one named place, one function per rule, with the rule's name.
  That is the part that gets ported and cross-checked later, so it is the part worth
  keeping clean. Everything else is scaffolding.
- Timebox it and say the box out loud before starting.
- The build itself is implementation, so it follows the normal model handoff.
  `pause-after-planning` owns that rule; read it there.

## Phase 4. De-mock toward real data, in stages, when the question needs it

A prototype running on data you invented answers "does this look right" and nothing more.
Most of the value in a POC comes from this phase, not from the first screen.

Stages, in order:

1. A synthetic seed shaped to the mock, so the screen is navigable.
2. A real export from the real source (a CSV pull, a snapshot), so real names, real volume,
   and real gaps show up.
3. A live read-only connection to a non-production instance, so nobody has to re-export
   anything and the numbers move when the source moves.

Stop at the rung the question needs, and say which rung you stopped at. Read-only, against
a non-production instance, always. A POC never writes to a real system.

Volume belongs here too. Real row counts change the answer, and a query that is fine on a
seed can be unusable on the real table.

## Phase 5. Get the answer from the person who owns it

- Show it, do not describe it. A live URL or a screenshot.
- If it renders, look at the rendered image, do not only measure it. A screenshot shows
  a clipped label or an empty panel that a passing measurement misses.
- Record each question's answer with the date and the person who gave it. A question nobody
  answered is not validated, no matter how good the prototype looks.
- A refutation is the best possible outcome. It deletes work. Report it as a win.

## Phase 6. Name what the POC could NOT validate. Required, never skip

This is the phase that gets dropped, and it is the expensive one. A POC that passes reads
as "the requirements are met", and everyone hears that claim as bigger than it is.

Enumerate, specifically:

- Rules the POC's data could not exercise. A rule that only differs when a customer has two
  or more orders is invisible in a seed that gives everyone one order. Ask, per rule,
  what input shape would make this rule disagree with the simpler rule I might have
  implemented instead, and whether the data contained that shape.
- Anything owned by a system or a team you cannot see. If the flow crosses into someone
  else's product, your POC has no opinion about that part.
- Anything the real stack does differently. Rounding defaults, null handling, an ORM versus
  a stored procedure, serialization casing, timezone handling, auth.

Each item becomes a REQUIRED conformance check in the implementation plan, run against the
authoritative definition owner rather than against the POC. Write the list into the plan.
It is the deliverable that outlives the prototype.

## Phase 7. Hand off, declare the oracle, then freeze

- State the oracle relationship explicitly. Run the real implementation and the POC over
  the SAME real input and compare outputs. Say in advance which one wins when they
  disagree, and on which axes.
- The moment the real implementation corrects a rule, the POC is stale on that rule. Record
  it the same day, in both repos' CLAUDE.md, naming the specific things that now differ.
- A stale POC still running is a demo that shows wrong numbers to whoever opens it. Either
  freeze it and label it, or retire it.

## Rules

- The POC answers a question. When it stops being about a question, it has become an
  unplanned second implementation, and that is a decision for the user to make, not a
  drift to discover afterwards.
- Never let the POC's data shape a rule. Data with no counterexample in it proves nothing.
- Never claim the POC validated more than it did. "The screen and the interaction are
  confirmed, the KPI arithmetic is not" is the honest sentence, and it is more useful than
  "validated".
- The POC is not a deliverable to a customer unless the user says it is.

## Worked example: what Phase 6 catches

Say a fast-stack prototype of a reporting screen is built first, because the real stack
cannot run locally. It goes past a mock, through a real export, to a read-only connection
against a staging database, and it settles the layout, the interaction, the sort order and
the empty states before the real implementation starts. It then becomes the oracle for
the port.

Now say the demo data gives every customer exactly one order. A rule such as "average
order value is the mean of a customer's paid orders, not the latest one" then agrees with
the wrong rule on every row, so neither the prototype nor the port can tell them apart.
The same goes for a count that a join silently multiplies, or a "completed" that must mean
paid AND shipped.

That is what Phase 6 exists for: the POC validated the UX contract, and it never had the
standing to validate the arithmetic. Written down at hand-off time, each of those rules
becomes a planned conformance check against the definition owner instead of a later
discovery.
