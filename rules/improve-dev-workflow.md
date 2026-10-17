# When something slips past the harness, improve the development workflow

When a real issue reaches you or a reviewer, and a skill, hook, agent or rule should have caught it first, that is a fault in the development process itself, separate from the bug. Run `/improve-dev-workflow` and turn the miss into a lasting upgrade of the artifact that should have caught it.

**Any one of these is a trigger:**

- A reviewer caught what authoring or a hook should have prevented.
- A test passed while the bug shipped, or a test turned out to check nothing.
- A hook fired on the wrong thing, or stayed silent when it should have fired.
- A rule existed but never ran against this project.
- The same mistake came back in a later session.
- A verification reported success while being unable to fail.
- You corrected a behaviour you have corrected before.

**These are not triggers:** an ordinary bug that the process caught as designed, and a one-off that no artifact could reasonably have caught.

**Do it in the same session**, while the evidence is still there, and name the artifact that should have caught the miss. When none reasonably could, say so instead of inventing a rule: every later session pays to load it.

`/save-context` (and so `/close-session`) asks this question at the end of a session by itself, in its step 7. The `/improve-dev-workflow` skill ships in the [claude-maintenance-skills](https://github.com/eranw2000/claude-maintenance-skills) pack.
