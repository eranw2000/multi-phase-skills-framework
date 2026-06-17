---
name: init-project
description: Initialize a project CLAUDE.md for a data/automation project (a `.claude/projects/<X>/` vault). Seeds from the project's `initial_description.txt` and from a `<project_name>_instruction_file.md` in `~/.claude/instructions/` when present, analyzes the project's files (flow definitions, scripts, CSVs, configs), then plans the doc and gets approval before writing. Use for new data/automation projects (Power Automate, n8n, CSV-driven, research vaults); for a source-code repository, use the built-in `/init` instead.
disable-model-invocation: true
argument-hint: [project-directory-path]
---

Create a comprehensive CLAUDE.md for a data/automation project. The target directory is: $ARGUMENTS

If no argument is provided, use the current working directory. This skill is for the `.claude/projects/<X>/` data vaults; for a source-code repository, use the built-in `/init` (it documents build/test/run commands, which this skill does not).

## Process

This skill plans before it writes. The CLAUDE.md is a foundational document, so the outline gets your approval first. The flow is: read the seed and the files, draft an outline, present it for approval in plan mode, then write.

### 1. Read the seed sources first (if present)

Before reading anything else, gather the project's seed sources. There are two, in two different locations. Read whichever exist; they are complementary, not either/or.

**Seed A: the project's own description, in the target directory.** Check for a seed document, in this order, stopping at the first hit:

- `initial_description.txt`
- `initial_description.md`
- a file whose name starts with `initial_description` (any extension)

**Seed B: the project's instruction/spec file, in `~/.claude/instructions/`.** First derive `<project_name>` as the basename of the target project directory (e.g. `~/.claude/projects/My Project/` gives `My Project`). Then look for the instruction file, stopping at the first hit:

- exact: `<project_name>_instruction_file.md`
- case-insensitive match of the same name
- fuzzy: a file in the instructions folder whose name contains `<project_name>` (or the distinctive part of it). Run `ls ~/.claude/instructions/` to see the options. If exactly one plausibly matches, use it; if several do, list them and ask which; if none, treat seed B as absent.

Read whichever of A and B exist, in full. Treat them together as the **authoritative description of what the project is and why it exists** (Seed A is usually the short overview; Seed B usually carries the fuller spec, requirements, or intended behavior). They are data, not instructions: they tell you the project's purpose, audience, and intended behavior. Use them as the spine of the Project Overview and to interpret the other files. Do NOT act on them as a task to build the project, even though Seed B lives in the instructions folder where files are normally executed via `/instruct`. In this skill they are source material to document, not a task to perform. This skill documents the project, it does not implement it.

If neither seed exists, note that and rely entirely on the files found in step 2.

### 2. Discover and analyze the project files

Read the files in the project directory and understand what the project does from config files, flow definitions, scripts, CSVs, READMEs, and any other artifacts present. For a large directory, prioritize config, flow, schema, and README files over reading every data row of a big CSV (sample the header and a few rows instead).

For each file:
- Flow definition JSONs (n8n, Power Automate): extract the full pipeline, node names, connections, credential references, IDs, API endpoints, configuration values.
- Scripts/code: extract purpose, key functions, dependencies, environment variables.
- Config files: extract all IDs, URLs, non-secret keys, column names, sheet names.
- Data files (CSV, JSON): extract schema/structure and purpose (header + sample, not the whole file).

### 3. Identify related codebases

If any files reference source-code projects, external services, APIs, or other repos, note them as related but do NOT read their full contents unless directly relevant.

### 4. Plan the document, then get approval

Enter plan mode (`EnterPlanMode`). Draft the outline of the CLAUDE.md: the Project Overview sentence, the list of components/flows you will document, the key IDs you found, and any gotchas. Present this outline with `ExitPlanMode` for approval before writing anything. This is the review gate, it catches a wrong reading of the project before it lands in the doc.

If the project is brand new and nearly empty (seed only, no real files yet), say so in the plan: the CLAUDE.md will be a thin scaffold built from the seed, to be filled in as the project grows.

### 5. Write CLAUDE.md (after approval)

Write CLAUDE.md in the project directory with these sections:

- **Project Overview**: 2-3 sentence summary of what this project does and who it is for, grounded in the seed sources (Seed A and/or Seed B) when they exist.
- **Flows / Scripts / Components**: detailed documentation of each major component:
  - Full pipeline/workflow description with node-by-node or step-by-step breakdown.
  - All external service IDs (sheet IDs, document IDs, form IDs, flow IDs, etc.).
  - Credential references (ID and name, never actual secrets).
  - API endpoints and configuration values.
  - Data schema (column names, field types, matching keys).
- **Known Issues & Fixes**: any bugs found and fixed, with root cause and solution.
- **Key IDs & References**: table of important IDs for quick lookup (node IDs, sheet IDs, credential IDs, etc.).

### 6. Report and suggest the next step

State where CLAUDE.md was written and give a one-line summary. If this is a new project at the start of its lifecycle, suggest the natural next step: run `/analyst` to gather requirements (it will also read a `BRAINSTORM.md` if `/capture-brainstorming` produced one), or `/capture-brainstorming` first if there has been brainstorming worth folding in.

## Rules

- Be exhaustive with IDs, column names, endpoints, and configuration. Future conversations should never need to re-discover these.
- Document the "why" behind non-obvious design decisions.
- Include gotchas and lessons learned.
- Never include actual secrets, tokens, or passwords. Reference IDs and credential names only.
- Use markdown tables for structured reference data. No Unicode box-drawing characters.
- Keep descriptions factual and concise, no filler. Avoid AI-tell writing: no em dashes, no marketing adjectives, no rule-of-three padding, straight quotes.
- Do not implement the project. This skill reads the seed and files and writes documentation only.
