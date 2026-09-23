# Measure a new guard against what is already live, before it ships

A guard (a hook, a lint rule, a CI check, a validation step) is written from the standard you wish held. It is enforced against a system built before you wished it.

**Run the new check over what is already in production, and say the number.** "The new rule flags 14 of the 212 files on main" is the result to report. If what is live would fail, the guard is not protecting a standard. It is blocking the future while the present breaks the rule, and the first person it stops has a better case than you do.

**The fix is not to weaken the check.** Add a recorded, named waiver instead:

- the check still runs on the waived item,
- its verdict is kept, not hidden,
- the person who overruled it is named on the waiver.

A guard with no such route gets deleted by whoever meets it at the end of a long day.

Before you ship the guard, also prove it can fire: break the thing it protects on purpose, watch the guard go red, then put it back.
