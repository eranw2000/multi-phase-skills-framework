# When your fix keeps containing the next bug, stop patching instances and find the rule

You fix one finding, and the lines you just wrote contain the next one. The review after that finds a third in the second fix.

**The signal is free: you fix finding N, and the next round finds N+1 in the lines you just wrote. Twice in a row means stop.**

Then ask a different question. Not "is this the same finding as last time?" but "would ONE rule have prevented all of these?" The two questions reach different answers. Instance fixes cover the variants someone described. A rule also covers the variants nobody has described yet.

How to find it:

1. **Name the mechanism** that produced every instance, in one sentence. Not "the regex missed X, then Y", but for example "the check matches a name without confirming the text around it is code".
2. **Look for a second channel through the same mechanism.** If one input path has the flaw, others that share the mechanism usually do too.
3. **Fix the rule, then re-test every earlier instance** against it, plus at least one new variant you invent.

**Route the rule to whatever owns the specification, not only to the code.** If the code followed the specification and is still wrong, the specification is wrong, and fixing only the code leaves the next implementation to repeat the mistake.

**A fix that removes or narrows text is safer than a fix that adds a list or an exception.** New wording in a fix round is a first draft. Give it the same scrutiny as the first round, because that is where the next bug usually sits.
