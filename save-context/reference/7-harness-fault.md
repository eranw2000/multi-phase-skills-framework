### 7. Ask whether this session exposed a fault in the harness itself

A save records what happened. This step asks a different question: did something reach the user, or reach a reviewer, that a skill, a hook, an agent or a rule should have caught first? That is a fault in the harness, and it costs more than the session's other lessons because it repeats.

Decide from the transcript you read in step 1, not from recall. Any ONE of these fires it:

- A reviewer caught what authoring or a hook should have prevented.
- A test passed while the bug shipped, or a test turned out to be vacuous.
- A hook fired on the wrong thing, or stayed silent when it should have fired.
- A rule existed but never ran against this project.
- The same mistake recurred across sessions.
- A verification reported success while being unable to fail.
- The user corrected a behaviour they have corrected before.

None of these fires it:

- An ordinary bug the process caught as designed. That is the process working.
- A one-off that no artifact could reasonably have caught.
- A lesson that only needs writing down. This step is for a fault with an owner, and plain recording is what the rest of this save already does.

**When one fires, ASK the user whether to run `/improve-dev-workflow` now.** One `AskUserQuestion`, one keystroke, with **Run it now** as the recommended option. Name the incident and the artifact that owns it in the question, so the user is choosing about a specific fault rather than about a skill name. Options:

- **Run it now (recommended).** The evidence is live only while the session is, so a deferred improvement is usually a lost one.
- **Skip it.** Then write the workflow improvement as an OPEN action item in step 8, naming the incident, the artifact that should have caught it, and the transcript path, so the lesson survives the session even though the improvement did not run.

**Ask ONCE, and only when a trigger actually fired.** No trigger means no question: a save that asks about a harness fault every time trains the user to dismiss it. And when several triggers fire, ask one question about the set rather than one per incident.

**Do not ask when there is nobody to answer.** In a scheduled or headless run a question only stops the work, so run `/improve-dev-workflow` by itself there and say in the report that the ask was skipped because nobody was there to answer.

That skill weighs the incident itself and does the light version when the fault sits in one artifact, so answering yes does not commit the user to a long loop. Say so in the question when the fault looks like a one-artifact fix.

**Name the artifact that should have caught it.** When no artifact reasonably could, say that in the report and write no rule. A rule invented to look thorough is worse than none, because every later session pays to load it.

This runs BEFORE the action items below on purpose. An improvement run produces follow-up work, and the sweep in the next step is what turns that work into items the user can see.

