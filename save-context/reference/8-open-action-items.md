Sweep the session for action items that are still OPEN: work discussed, planned, deferred, parked or flagged as a follow-up but NOT finished. Do not ADD a completed item, and skip session noise.

**Then mark what this session FINISHED.** An existing item that the session completed is marked done, struck where it sits (the todo format's "Done means finished"), never deleted and never left open. A finished piece of work with no item of its own is not added to the TODO; it is recorded as a status change in the project CLAUDE.md by step 4.

Run the `todo` skill's workflow (`~/.claude/skills/todo/SKILL.md`) against the active project:

- Resolve the project as step 2 did, and target its `~/.claude/projects/<X>/TODO.md`, creating it from the template if absent.
- Add each open item to the right bucket: in-flight or next-up work to **Active**, not-yet-started but intended to **Queued**, blocked or contingent to **Parked**. Carry a due date as `(due YYYY-MM-DD)` when the session named one.
- Check the existing items first, so you update or skip a duplicate instead of stacking a second copy. Honor the file's existing bucket structure per the todo format rules.
- **Correct an item this session made false**, not only add new ones. An item that is wrong costs more than an item that is missing, because it sends the next session to redo finished work.
- Run the todo skill's auto-sync (`~/.claude/skills/todo/todo-format.md`, section "Auto-sync rule") ONCE after the adds, not per item. It updates the cross-project index and the project memory's open-items hook, which is the half a save otherwise leaves stale.

Edit the real `TODO.md` markdown file. Never satisfy this with the ephemeral TodoWrite tracker.

If nothing is genuinely open, write nothing and say so in the report. A save that invents an item to look thorough is worse than one that adds none.

**Why a save does this and not only a close.** A save is the only guaranteed end-of-session write. `/close-session` is skipped whenever the session keeps running, and a save is often run mid-session precisely because a close would tear down shells and jobs. So if the item sweep lives only in the close, every session that ends without one loses its open items and the pin becomes the sole record, which it is too short to be.
