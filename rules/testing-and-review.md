# Testing and review integrity

The through-line: real bugs are found by **executing** the actual input through the actual path. Misses come from reasoning about code. And a test that passes without exercising what it claims agrees with its author every time.

## Default proof is light

For an ordinary change: **tests that fail without the change, plus one review.** Prove a new test is real by reverting the change once, watching the test go red, and restoring it.

Heavier proof (a mutation run, frozen test lists, repeated review rounds) is for changes that can **delete data, kill or signal processes, or touch production** (deploys, releases, live services, credentials), or when the user asks for it.

## What makes a test real

- **Watch it fail first.** A test you never saw go red may be testing nothing.
- **Enter where production enters.** A test that calls a helper directly can pass while the real entry point never reaches that helper. Name the caller production uses and make at least one test go through it.
- **Assert the result, not the decision.** "A change was queued" is not "the change was delivered". Check the output the user would see.
- **A fixture must not read shipped config.** If the fixture would have to change when the product reaches a state it is designed to reach, it is bound to today's release, not to the contract. Build the fixture's own data.
- **A test that goes red when you fix a bug may have been asserting the bug.** Move it onto an input that really has the property it names, and keep a contrast case for the new behaviour. Never just relax the assertion.
- **A new test must fail, never crash, when the feature is absent.** A crash can end the file and silently skip every test after it.
- **A timed test must not pass because time ran out.** Test the logic with a long deadline or a controlled clock; keep one separate real-time test for the budget itself.

## Checks that cannot fail

A check built on `grep` or a filter can match nothing and print an empty result, which looks exactly like "clean".

- **Give every verification loop a control row whose answer you already know.** If the control prints nothing, the checker is broken, not the code.
- **Prove it both ways.** One control shows the check catches a real positive; another shows it ignores the decoy.
- **Strip colour codes** from tool output before matching it.
- **A count is not a scope.** Print the list you measured, not only the total.

## Mutation and contrast

When the change is in the risky class above:

- Break each guard on purpose and confirm a **named** test goes red. A guard no test catches is unproven.
- A survivor can mean the guard is dead, or that a later check masks it. Add a case only that guard can catch; never weaken an assertion to get a kill.
- Run mutations in a throwaway copy, never in the working tree.

## Reviews

- **A reviewer's verdict is information for the user, not an instruction.** Bring the findings to the user and let them choose what to fix.
- **Re-review the fix commit.** A fix round writes new code, and new code is a first draft.
- **Reproduce a finding by running it before fixing it.** A finding you cannot reproduce may be wrong.
