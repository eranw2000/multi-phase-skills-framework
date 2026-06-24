# Authoring and packaging guide

The method behind this framework, and a reusable playbook for building your own packs of Claude Code commands, skills, and agents to share with a team. It is generic on purpose: derive paths from `$HOME`, keep personal and project specifics out. `~/.claude/...` is the standard Claude Code config location every user has.

`framework-flows.drawio` / `framework-flows.png` in this folder show the phase chain visually.

## 1. The three artifact types, and when to use each

Claude Code has three user-extensible artifact types. A pack usually ships a mix.

**Command** (`~/.claude/commands/<name>.md`). Frontmatter: `description`, optional `argument-hint`. The body is a prompt template; `$ARGUMENTS` interpolates what the user typed. Invoked explicitly as `/name`. Use for a repeatable, parameterized prompt or workflow the user deliberately triggers.

**Skill** (`~/.claude/skills/<name>/SKILL.md`). Frontmatter: `name`, `description`, optional `disable-model-invocation` and `argument-hint`. The body is instructions; the directory can bundle `scripts/`, `references/`, and `assets/`. The model can auto-invoke a skill from its description, or the user can call it. Use for a capability or methodology the model should reach for, especially when it benefits from bundled scripts or reference files.

**Agent** (`~/.claude/agents/<name>.md`). Frontmatter: `name`, `description`, and `tools` (the allowed tool list). The body is the agent's system prompt. Spawned as a subagent with its own context window, it does a focused task and returns a result. Use for delegated work that benefits from isolation, a constrained toolset (for example a read-only reviewer), or parallel fan-out.

**Choosing:**
- User must type a trigger and pass arguments, output goes back into the conversation: **command**.
- The model should pick it up by intent, or it needs bundled resources, or it encodes a multi-step methodology: **skill**.
- The task should run in isolation, with a narrow toolset, or several in parallel: **agent**.

These compose: a skill can spawn agents; a command can invoke a skill.

## 2. Authoring quality

**The description is the triggering mechanism** (for skills and agents). State both what the artifact does and when to use it. They tend to under-trigger, so descriptions should lean slightly "pushy" (fire even when the user does not name the artifact or file type). Add negative-scope clauses ("not for X, use Y instead") to prevent collisions with siblings.

**Progressive disclosure (skills, three levels).** Metadata (name + description) is always in context. The body loads when the skill triggers. Bundled resources load only when needed. Keep `SKILL.md` short; push detail into reference files with clear pointers.

**`disable-model-invocation`.** True for artifacts that should only run when the user explicitly invokes them; false (default) for ones the model may auto-trigger.

**Three ways to create an artifact:**
- Hand-write it (good when the procedure is short and already clear).
- Distill it from a real working session (best for capturing a proven methodology, including the gotchas).
- Use Anthropic's skill-creator (the packaging and tuning layer on top of the other two; it also handles agents).
Recommended default: distill from a real session, then run it through skill-creator for structure and description-tuning.

**Validation ladder** (depth to taste): structural check (valid frontmatter, name matches directory, no broken bundled references) → qualitative review (structure, triggering, clarity, scope, dangling references) → quantitative description-optimization loop (tests ~20 should-trigger / should-not-trigger queries and auto-tunes the description) → full output eval (run the artifact on test prompts with baselines). For subjective workflow artifacts, structural + qualitative is usually enough; the description-optimization loop is the highest-value rigorous add-on, because mis-triggering is the most common failure.

## 3. De-personalization checklist (run on every artifact bound for another team)

- Remove the personal name; address the reader as "the user" or "you".
- Remove machine-specific absolute paths. Derive locations from `$HOME`. For the cross-project memory/index area, use a dash-encoded home-path placeholder (for example `-Users-<username>` for `/Users/<username>`) and derive it at runtime.
- Remove references to skills, commands, or agents not shipped with the pack, and to a personal global config file. Inline the relevant rule (for example a plain-prose writing rule) instead of citing an external global file.
- Drop project-specific examples from bodies.
- Generalize defaults: do not assume `main` as the branch; use generic tracker names rather than one vendor.
- Sweep for dangling references after editing: any artifact name in the text that is not in the pack should be removed or documented as an external dependency.

**Writing conventions (all prose, docs, commit messages):** no em dashes, no AI-tell vocabulary, no rule-of-three padding, straight quotes, no Unicode box-drawing characters in tables (use markdown pipe tables or lists).

## 4. Packaging and distribution

**Repo layout.** Each skill is a self-contained directory (its `SKILL.md` plus bundled helper files, kept together). Commands and agents are single `.md` files, grouped under `commands/` and `agents/`. The repo lives in a normal source tree, not inside `~/.claude`.

**Install locations** (spell these out in the README): commands to `~/.claude/commands/`, skills to `~/.claude/skills/`, agents to `~/.claude/agents/`. Install is a copy (or symlink) into those directories. Copy only the artifact directories, not the repo's own README/LICENSE/docs.

**For shipping at scale, consider a plugin/marketplace** instead of copy-in: a plugin bundles commands, skills, agents, hooks, and MCP servers together and installs/updates as a unit. Copy-in is fine for a small pack; a plugin is better when a team will track updates over time.

**README must document:** what each artifact does, the install steps per type, any dependencies or companions NOT bundled (so dangling references are explained rather than surprising), and the baked-in conventions.

**Licensing and attribution.** If any artifact is adapted from a third-party set, check that set's license. For MIT: redistribution and adaptation are fine as long as the copyright and permission notice are retained. Then:
- Put a short "Based on ..." comment at the top of each derived artifact's body; leave original artifacts uncredited.
- Ship a LICENSE (MIT, with dual copyright when partly derived) and a NOTICE documenting which files derive from the upstream set. Credit the upstream in the README.
- Keep the in-file credit clean; do not reference a personal install command the team cannot run.

**Private config-repo pattern (for your own `~/.claude`, never public).** A personal `~/.claude` can be a private git repo using an allowlist `.gitignore`: ignore everything (`/*`), then explicitly un-ignore the safe paths (the artifact dirs, `settings.json`, loose config scripts, the global doc and its satellites, and only the memory subfolder of the projects area). Add a never-track block for `.env`, `*.key`, `*.pem`, credentials, and eval scratch dirs. This is the opposite stance from a public framework repo: the config repo is private and personal; the framework repo is public and de-personalized.

## 5. Design philosophy: modular vs monolithic

A monolithic framework ships one large, hook-injected, mandatory end-to-end methodology. A modular framework ships small, single-purpose, composable artifacts the user triggers as needed (the instinct Anthropic's own official plugins follow). Default to modular: each artifact does one thing, is usable on its own, and composes with the others. It is easier for a team to adopt incrementally, easier to review, and less likely to collide with their existing setup. This framework is modular by design.

## 6. This framework as a worked example

A chain of phase skills, each producing one named handoff artifact so the next phase starts warm. Each skill is also usable on its own. (See `framework-flows.png` for the visual.)

1. **capture-brainstorming** produces `BRAINSTORM.md` (full capture, or cheap repeatable checkpoints). Hands deferred action items to the todo skill.
2. **analyst** produces `REQUIREMENTS.md`: the problem space (WHAT and WHY), testable FRs and measurable NFRs, each with an ID.
3. **architect** produces `SPEC.md` plus an architecture diagram, gating on a complete REQUIREMENTS.md first and a user-confirmed SPEC.md before slicing.
4. **prd-to-issues** breaks the spec into tracer-bullet vertical-slice issues; first slice is a walking skeleton.
5. **tdd** implements each issue with red-green-refactor, one slice at a time.

Supporting skills: **grill-me** (adversarial stress-test), **init-project** (seed a project doc), **todo** (persistent per-project TODO with a cross-project index), **write-a-prd** (lightweight single-feature alternative to analyst-then-architect), **save-context** and **close-session** (end-of-session persistence). A start-of-session briefing ships as a `/new-session` command in the companion commands pack, not as a skill here.

Conventions worth reusing: stable IDs (FR-N, NFR-X-N, D-N) thread requirements through design, issues, tests, and review; vertical tracer-bullet slicing with a walking skeleton first; the brainstorm output is a handoff artifact, not memory; an open topic (a decision) is kept separate from an action item (a task handed to the todo skill), never double-tracked.
