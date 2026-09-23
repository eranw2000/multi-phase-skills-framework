# Model routing: plan on the strongest model, build on a strong one, route routine work to a fast one

Three tiers, pinned with the `model:` line in the frontmatter of skills, agents and commands:

- **`fable`** for planning and judgment-heavy review.
- **`opus`** for execution and quality-sensitive content.
- **`sonnet`** for routine or mechanical work.

Apply the same routing to any new skill, agent or command you write, and to any built-in agent you spawn.

**A pin lasts only the turn that invoked the artifact.** After that turn the session model is back in charge. So a multi-turn planning session needs an explicit `/model` switch to the planning tier, and an implementation session needs a switch back.

**The switch point is the first code edit, not plan approval.** Evidence gathering, audits and strategy work are analysis and stay on the planning model even after a plan is approved. `/pause-after-planning` in this pack arms a stop at that boundary.

**Check which model is serving before you say which one is.** Read it from the session transcript (the `message.model` field of the newest entry in the session's `.jsonl` file under `~/.claude/projects/`), not from memory or from the system prompt. Never state a model without that check in the same turn.

**The user sets the model.** Never stop a run to ask for a switch. Say which model is serving, then carry on under it.

If a pinned model is not on your plan, edit or delete the `model:` line; a missing pin inherits the session model.
