---
name: save-context
description: End-of-session context save — updates project CLAUDE.md and optionally global CLAUDE.md with discoveries, decisions, and lessons from the current conversation. Use when the user says "save context", "save session", "/save-context", or wants to capture this session's learnings without closing the session. For save plus cleanup, use close-session instead.
disable-model-invocation: false
---

# Save Session Context

Review the entire conversation and persist all valuable context for future sessions. This runs at the end of a conversation before closing.

## Steps

### 1. Identify the active project
- Determine which project was worked on based on the conversation context and working directory
- Locate the project's CLAUDE.md file (in `.claude/projects/` for the project)
- If no project CLAUDE.md exists yet, create one with a clear structure

### 2. Update the project CLAUDE.md
Read the current project CLAUDE.md, then update it with anything new from this conversation:

- **Decisions made** — design choices, architectural decisions, trade-offs discussed with the user
- **Features implemented** — what was built, how it works, key implementation details
- **Bugs fixed** — what went wrong, root cause, how it was resolved
- **Gotchas discovered** — non-obvious behavior, edge cases, things that broke unexpectedly
- **Configuration changes** — new IDs, endpoints, env vars, column names, API details
- **Status updates** — mark "Planned" items as implemented, update version numbers
- **Lessons learned** — patterns that worked, patterns that didn't, things to avoid next time

Do NOT duplicate information that's already in the file. Update existing sections when the information has changed. Remove outdated content.

Keep it factual, structured, and concise. Use the existing document structure and style.

### 3. Check if global CLAUDE.md needs updating
Review whether anything from the conversation applies across ALL projects (not just this one):

- **New workflow patterns** — e.g., a deployment technique, API access method, or tool usage pattern that applies everywhere
- **user's preferences** — working style, communication preferences, or tool choices that should persist globally
- **Credential/access updates** — new tenant IDs, app registrations, CLI tools configured
- **Cross-project references** — links between projects discovered during this session

If yes, update `~/.claude/CLAUDE.md` with the relevant information.
If nothing is globally relevant, skip this step — don't add noise.

### 4. Update memory if needed
If any of the following were discovered during the conversation, save or update the appropriate memory files:

- New information about user's role, preferences, or expertise → `user` memory
- Feedback on how to approach work → `feedback` memory
- Project context not derivable from code → `project` memory
- External resource references → `reference` memory

Only save memories for information that will be useful in **future** conversations and isn't already captured in CLAUDE.md files.

### 5. Report what was saved
Briefly list what was updated:
- Which CLAUDE.md file(s) were modified and what sections changed
- Any new memory files created or updated
- Key items preserved for future sessions

## Key Principles
- Capture the **why** behind decisions, not just the **what**
- Don't save ephemeral task details — focus on durable knowledge
- Don't duplicate what's already in git history or the code itself
- Prefer updating existing sections over creating new ones
- If nothing meaningful was discovered, say so — don't pad the files with noise
