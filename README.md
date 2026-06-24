# Multi-Phase Skills Framework

A set of Claude Code skills that take a piece of work through distinct phases, from a rough idea to tested code, with a clear handoff artifact at each step. Each phase is small and does one thing, so you can start anywhere in the chain and stop when you have what you need.

## The phase chain

The skills are designed to run in this order, but each is usable on its own.

1. **capture-brainstorming** — turn an exploratory thinking session into a `BRAINSTORM.md` handoff log. Runs as a full capture (mines the conversation plus past session transcripts) or as a cheap checkpoint you can repeat during a long session. Surfaces deferred action items and hands them to `todo`.
2. **analyst** — interview the user and the codebase, then write `REQUIREMENTS.md` (the problem space: WHAT and WHY, not HOW). Warm-starts from `BRAINSTORM.md` when one exists.
3. **architect** — read `REQUIREMENTS.md`, decide the design with the user, write `SPEC.md` plus an `architecture.drawio`, then slice the work via `prd-to-issues`.
4. **prd-to-issues** — break a plan or spec into independently-grabbable, tracer-bullet vertical slices as issues on the project tracker. First slice is always a walking skeleton.
5. **tdd** — implement each issue with the red-green-refactor loop, one vertical slice at a time. Hands the branch off for review and a PR per your team's process.

Supporting skills used across the chain:

- **write-a-prd** — lightweight single-feature alternative to the `analyst` then `architect` pass: one interview, one PRD, filed as one issue. Based on the Matt Pocock skills set.
- **grill-me** — adversarial interview to stress-test a plan, design, or doc before committing to it. Based on the grill-me skill by Matt Pocock.
- **init-project** — seed a project `CLAUDE.md` for a data/automation project from its description and files.
- **todo** — persistent per-project `TODO.md` with a cross-project index. Other skills hand deferred work to it.
- **save-context** — end-of-session save into the project `CLAUDE.md` and memory.
- **close-session** — save-context plus teardown of resources this session started.

A start-of-session briefing is available separately as the `/new-session` command in the companion commands pack; it is not bundled here.

## Install

Each subdirectory here is a self-contained skill (a `SKILL.md` plus any helper files). To use them, copy or symlink the skill directories into your `~/.claude/skills/` so Claude Code picks them up:

```bash
# Copy only the skill directories (those containing a SKILL.md),
# skipping docs/ and the repo's own README/LICENSE/NOTICE.
for d in multi-phase-skills-framework/*/; do
  [ -f "$d/SKILL.md" ] && cp -R "$d" ~/.claude/skills/
done
```

`tdd` and `todo` ship with companion files next to their `SKILL.md` (reference notes and helper scripts); keep each skill's directory intact when you copy it.

The persistence skills (`capture-brainstorming`, `analyst`, `todo`, `save-context`, `close-session`) assume the standard Claude Code layout: a per-project data dir at `~/.claude/projects/<X>/` and a memory index under the dash-encoded home path (e.g. `-Users-jdoe` for `/Users/jdoe`). They derive that path from `$HOME`, so they work on any machine without editing.

## Dependencies and companions (not bundled)

These skills reference a few things this framework does not include. None are required to use the core chain; they are points where the framework hands off to your own tooling.

- **Review and pull-request / checkpoint step after `tdd`.** The framework deliberately does not prescribe a review or PR tool. When tests are green, `tdd` tells you to hand the branch off for review and open a PR per your team's process. Plug in whatever you use (a code-review skill, your CI, a manual review).
- **OpenSpec (optional, `architect` Path A).** `architect` defaults to slicing straight into issues via `prd-to-issues` (Path B). It can instead scaffold an OpenSpec change if your repo already uses OpenSpec, which is a separately installed tool (`npm install -g @fission-ai/openspec`). Skip it unless your team has standardized on it.

## Conventions baked in

- Every phase produces one named artifact (`BRAINSTORM.md`, `REQUIREMENTS.md`, `SPEC.md`, issues, code) so the next phase starts warm instead of cold.
- Requirements and decisions carry stable IDs (FR-N, NFR-X-N, D-N) so issues, tests, and later review can all anchor to them.
- Writing follows plain-prose conventions: no em dashes, no marketing adjectives, no Unicode box-drawing characters in tables (markdown pipe tables are fine).

## Credits

Several skills here are based on Matt Pocock's open-source skills set (https://github.com/mattpocock/skills): `tdd`, `prd-to-issues` (his `to-issues`), `write-a-prd`, and `grill-me`. To install his full upstream set and its per-repo config, run `/setup-matt-pocock-skills` from that repo. `analyst` and `architect` are original to this framework, they add the explicit requirements and design phases his set does not include.

## License

MIT. See [LICENSE](LICENSE) and [NOTICE](NOTICE). The skills derived from Matt Pocock's set are used under its MIT License, with his copyright retained.
