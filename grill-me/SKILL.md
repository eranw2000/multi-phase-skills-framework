---
model: fable
name: grill-me
description: Interview the user relentlessly about a plan, design, or document, walking the decision tree in dependency order until every weak spot is fixed or accepted. Asks one question at a time with a recommended answer, and explores the codebase rather than asking what the repo answers. Leaves NOTHING open, so an unresolved point becomes a question to the user, never a silent assumption. Defines every term the subject leans on but never explains, writing it to the repo CONTEXT.md glossary so later steps share one vocabulary. Takes an optional file path (e.g., "/grill-me SPEC.md"), else grills the plan in the conversation. Reusable on a rough idea, REQUIREMENTS.md, or SPEC.md. Use when the user wants their plan challenged or stress-tested, says "grill me", "stress-test this", "poke holes in", "define the terms", or wants a reviewer pass before committing. Also offers ADRs for one-way decisions where the repo uses them. Adversarial but constructive.
argument-hint: "[optional path to a doc to grill, e.g. BRAINSTORM.md, REQUIREMENTS.md, SPEC.md]"
---

# Grill Me

<!-- Based on the grill-me skill by Matt Pocock (https://github.com/mattpocock). -->

Interview the user relentlessly about every aspect of a plan, design, or document until you reach a shared understanding. Surface every objection a careful reviewer would raise. Walk down each branch of the decision tree, resolving the dependencies between decisions one by one. Drive each to a resolution: either the design holds (record why) or it changes (update accordingly). Do not stop until every branch is resolved.

## Input

- If the user passed a path as an argument (e.g., `/grill-me REQUIREMENTS.md`, `/grill-me docs/proposal.md`, `/grill-me openspec/changes/add-auth/design.md`), read that file first. That file is the subject of the grilling.
- If the argument is a URL, fetch it and use the content as the subject.
- If no argument is given, the subject is whatever plan or design is in the current conversation.
- The subject can be at any stage: a rough idea or BRAINSTORM.md before you commit to a path (write-a-prd or analyst), or a written REQUIREMENTS.md / SPEC.md before the next phase.

State clearly at the start which subject you are grilling.

## Find the spec that belongs to your initiative

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

Grilling the wrong initiative's document produces sharp questions about the wrong system, and every one of them reads as competent.

## Process

### 1. Absorb the subject

Read it fully. Build a list of every:
- Claim or assertion
- Assumption (stated or implicit)
- Decision (with or without alternatives noted)
- Constraint
- Unstated implication
- Term the subject leans on and never defines (see "Every term has to be clear")

### 2. Generate the strongest objections

For each item above, ask what the most rigorous reviewer would object to. Categories:
- Hidden assumptions
- Edge cases not addressed (empty, very large, concurrent, time-zoned, locale-varied, network-partitioned)
- Missing failure paths and recovery behavior
- Constraints that conflict with stated goals
- Non-functional gaps: performance, security, observability, cost, accessibility
- Coupling that makes the design fragile or hard to change
- Decisions made without alternatives considered
- Vocabulary used inconsistently, or a load-bearing term never defined at all
- Open questions left as "we will figure it out later"

### 3. Walk the tree, one question at a time

Treat the objections as a decision tree. Order them by dependency: a decision that other decisions hang on gets resolved before the ones that depend on it. Do not jump around the tree; resolve the dependencies between decisions one by one.

**Ask one question at a time.** Present the single strongest objection in the most fragile branch, then stop and wait for the answer. Do not batch questions or dump a numbered list. The interview is a back-and-forth, not a questionnaire.

**For every question, provide your recommended answer.** State the objection, the consequence, and then your own recommendation with its reasoning. The user reacts to a concrete proposal instead of starting from a blank page. Recommend, do not impose: the user makes the call.

**If a question can be answered by exploring the codebase, explore the codebase instead of asking.** Before putting a question to the user, check whether the answer already exists in the code, config, tests, or docs. If it does, go read it and resolve the branch yourself, then report what you found. Only escalate to the user the questions that genuinely need their judgment or knowledge that is not in the repo.

**NOTHING is left open. When you cannot resolve a branch, ASK the user.** This is the rule the others hang off, so read it before the four resolutions below. A branch you cannot settle from the subject or the repo is a question for the user, and asking is the skill working rather than the skill failing. Never close a branch by picking the likelier reading, by deferring it to "we can decide during implementation", or by writing an assumption you did not put to them first. Silence is not agreement and neither is a plausible guess: both convert a decision the user owns into one nobody made, and the cost lands later, when it is expensive and nobody remembers who chose.

The test to apply before ending the interview: if a reader asked "what did you decide about X, and who decided it?", every branch must have an answer and a name. A branch whose answer is "we did not get to it" means the grill is not finished.

Resolve each branch one of four ways:
- The design holds: record the reasoning so the next reader does not have to re-derive it.
- The design changes: update the subject document accordingly.
- The risk is accepted as-is: mark it explicitly as an accepted risk with a one-line justification. Accepting is the USER's verb, never yours.
- The answer genuinely cannot exist yet: record it as a **stated assumption** in the subject document, written as a claim that can later be checked ("we assume every order has exactly one customer"), never as a lingering question. An assumption someone can falsify is worth far more than an open question nobody returns to.

**The fourth resolution is not an escape hatch, and it is the one that will be abused.** It is available in exactly two situations. Either the user is not present, which in practice means an autonomous run. Or the user IS present, you asked, and the honest answer is that it depends on something not yet decided or not yet known, such as a vendor's reply or a measurement nobody has taken. In the second case the user still hears the question and still chooses to defer, so the deferral is a decision they made rather than one you made for them. Every stated assumption names who would confirm it and what would falsify it. If you cannot name either, you have not asked enough.

Then move to the next branch. Do not stop early because "most" branches are done. Keep going until shared understanding is reached on every branch. The unaddressed ones are exactly where the bugs live.

**When the grill invalidates the DESIGN rather than the wording, stop and say so.** Some branches do not resolve into an edit: they show the document is a faithful description of an approach that does not hold. Continuing to reword around that produces a document that reads well and specifies the wrong thing. Name it, recommend returning to the design step (`/architect` where SPEC.md came from one), and end the grill rather than patching prose over it.

### 4. Anchor every objection

Each objection must have a concrete consequence: "if X happens, Y breaks". Abstract concerns ("this feels wrong") are nits and go at the end. Do not soften. Do not invent objections to seem thorough.

### 5. Wrap up

Summarize:
- What changed in the subject
- What was accepted as-is, with the justification
- What was recorded as a stated assumption, and who would confirm each one
- Which terms were defined, and where the glossary lives
- Recommended next step (revise the doc further, hand off to architect, abandon the approach, etc.)

**State plainly that nothing was left open, or do not end.** The wrap-up carries no "open questions" list, because reaching the wrap-up means there are none. If you find yourself about to write one, the interview is not over: go back and ask those questions. The single exception is a branch the USER chose to defer, which is reported as their decision, with what it waits on and who would settle it, never as a loose end.

## Every term has to be clear, and the unclear ones go in CONTEXT.md

Always active, and this is the one thing that changed: the vocabulary work used to run only in a repo that already kept a `CONTEXT.md` or a `docs/adr/`, so most repos got no glossary at all. It now runs everywhere, and creates `CONTEXT.md` lazily in a repo that has never had one.

The file is deliberately the existing one rather than a new `GLOSSARY.md`. A glossary nothing reads is worth nothing, and `CONTEXT.md` is the name other tools already look for. A second filename would have been invisible to every one of them.

An undefined term is an open question wearing a noun, and it is the one kind of open question that does not look open: two people read the same sentence, agree, and disagree about what it meant. That disagreement surfaces much later as a defect nobody can attribute, because the document really did say the thing they both agreed to.

**Collect the terms during step 1 and challenge them during step 2.** A term needs a definition when the subject leans on it and never says what it is, when two parts of the subject use it differently, or when you could write two defensible definitions and the choice would change what gets built. A term is fine undefined when it is ordinary English used ordinarily. Do not pad the glossary with words nobody would misread, and note that CONTEXT-FORMAT.md's rule is stricter still: a general programming concept does not belong even when the project uses it constantly.

**Try the repo before you ask.** The same rule as any other branch. Code, tests, config, existing docs and prior glossaries often already define the term, and reading is cheaper than asking. Ask the user only for what the repo cannot answer.

**A term you cannot define is a QUESTION, not a guess.** Put it to the user as its own branch, with your recommended definition and what turns on the choice. Never invent a definition and carry on. A wrong definition written confidently is worse than a missing one, because the missing one still gets noticed.

**Write each term the moment it is settled, not at wrap-up.** An interview that gets interrupted keeps what it settled. Create the file lazily on the first term.

**Which file.** `CONTEXT.md` at the repo root. In a multi-context repo a `CONTEXT-MAP.md` at the root lists the contexts and where each one's copy lives, so write to the relevant context's copy rather than the root. When the subject exists only in the conversation and there is no repo, put it in the project data directory beside the subject. Never create a second vocabulary file under any name; one per context is the whole point.

**Format: [CONTEXT-FORMAT.md](CONTEXT-FORMAT.md), which owns it.** Do not restate the layout here or invent a variant. It carries the term shape, the `_Avoid_` list for rejected synonyms, the one-or-two-sentence limit, the be-opinionated rule, the project-specific-terms-only rule, and the multi-context map. What matters at this level is only what the file is FOR: vocabulary, never spec fragments, never implementation notes, and never a place to park a decision that belongs in the subject document.

**It is meant to be USED, not just written.** Read it at the start of every run when it exists, and treat a conflict between the subject and an existing definition as its own branch, exactly as the docs trail already did. From then on use its word everywhere: in your questions, in the edits you make to the subject, and in the wrap-up. Point the next step at the file by name so the vocabulary survives the handoff, which is the only reason the file is worth keeping.

## ADRs (optional)

This section used to cover the glossary too, and gated BOTH halves on the repo already having a `CONTEXT.md` or a `docs/adr/`. Vocabulary moved out and is now always active, owned by the section above. Only the ADR half is still optional, and only it is gated.

Active when the repo already has a `docs/adr/` directory, or when the user explicitly asks for the paper trail. Otherwise skip this section entirely; the grilling and the vocabulary work behave exactly as described above. This is a set of inline writes, never an invocation of another skill.

When active:

- **Offer ADRs sparingly (during step 3).** When a resolution is (1) hard to reverse AND (2) surprising without context AND (3) the result of a real trade-off, offer to record it under `docs/adr/`. If any of the three is missing, skip the ADR. Most sessions produce few or no ADRs; a sharper glossary and zero ADRs is a normal outcome. Format: [ADR-FORMAT.md](ADR-FORMAT.md).
- **Report the ADRs in the wrap-up (step 5).** The terms are already reported there by the vocabulary rules above; add the ADRs written alongside the other outcomes.

## Output

- **If the subject was a file**: produce an updated version of the file reflecting resolutions. Save it. List accepted risks in their own section, and stated assumptions in their own section, each phrased as a checkable claim naming who would confirm it. There is no "Open Questions" section, because a finished grill has none; a branch the user chose to defer goes under stated assumptions with what it waits on.
- **If the subject was an in-conversation plan**: produce a summary message with resolutions, accepted risks and stated assumptions.
- **Either way**, name the glossary file and the terms settled in it, so the next step starts from the same vocabulary.

## Stance

- Adversarial but constructive. The goal is to make the design stronger, not to be right.
- An interview, not an interrogation dump. One question at a time; wait for the answer before the next.
- Resolve decisions in dependency order, walking the tree one branch at a time.
- Recommend an answer for every question, with reasoning. Recommend, do not impose; the user makes the call.
- Answer from the codebase whatever the codebase can answer. Only ask the user what the repo cannot tell you.
- Anchor in consequences, not abstract concern.
- Do not redesign on behalf of the user. Surface the issue, recommend a fix, let the user choose.
- Do not stop until every branch is resolved, changed, accepted-with-justification, or recorded as a stated assumption, and you share an understanding of the whole plan.
- Leave nothing open. What you cannot settle, ask. Asking is the skill working.
- Define every term the subject leans on and never explains, and use that word from then on.

## Guardrails

- Do not invent objections. Each must have a concrete consequence.
- Do not close a branch by guessing, by deferring it to implementation, or by writing an assumption you never put to the user. Ask instead.
- Do not invent a definition for a term you could not settle. An unasked term is an unasked question.
- Do not create a second glossary. One file per repo, and an existing `CONTEXT.md` wins.
- Do not write production code in this skill. If the user wants to implement a fix, exit to TDD or Developer.
- Do not silently rewrite the user's design. Propose, get agreement, then update.
