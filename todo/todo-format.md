# TODO.md format (shared protocol)

The canonical shape for every per-project `TODO.md` and for the cross-project index. Used by the `todo` skill (create + render + sync paths) and by `bulk_create_todos.py`. Keep all three consumers in step with this file.

## Where the files live

- **Per-project TODO.md:** `~/.claude/projects/<X>/TODO.md` (the project DATA dir, alongside the project `CLAUDE.md`). NOT the code repo.
- **Cross-project index:** `~/.claude/projects/<index-dir>/TODO.md` (the summary, one line per project). `<index-dir>` is the dash-encoded home path (e.g. `-Users-username` for `/Users/username`).
- **Memory:** there is NO single memory directory, and believing there is one is how a stale claim survives. A memory store follows the session's LAUNCH directory, so `project_*.md` files can be spread across several stores under `~/.claude/projects/*/memory/`. **Never name a store; RESOLVE the file, and print what you resolved so an empty answer is visible rather than silent:**

  ```sh
  FILES=$(find ~/.claude/projects -maxdepth 3 -path '*/memory/project_*<x>*.md')
  echo "$FILES"   # empty means the name did not match, NOT that the project is clean
  ```

Link conventions (relative):
- per-project TODO.md to a memory file: `../<store>/memory/project_*.md`, where `<store>` is whichever store the resolver above returned. Resolve it; do not assume it.
- index to a memory file: `memory/project_*.md`
- index to a per-project TODO.md: `../<X>/TODO.md`

## The five state buckets

In order of relevance. Every TODO.md uses this set. The bucket label after the dash is adaptable per project (e.g. "Parked / on hold" vs "Parked / contingent", "Queued v1.1"), but the five concepts and their order are fixed. Older files may separate the label with a dash instead; both forms are read.

1. **Active — concrete next steps now**
2. **Queued — agreed, awaiting the user's go-ahead** (do not start unsolicited)
3. **Parked / on hold — don't propose unsolicited**
4. **Live (monitor only) — no action unless something breaks**
5. **Advisory — delivered, dormant unless re-engaged**

Not every project needs all five populated. An empty bucket can be dropped or left with a one-line "(none)".

## Item format

- Checkbox items: `- [ ] <one line>`. A finished item is struck, not deleted (see maintenance footer): `- [x] ~~<one line>~~`.
- One line per item plus a memory pointer. Do NOT duplicate detail that lives in the project `CLAUDE.md` or memory. The line is the index; the detail lives behind the link.

### Optional richer structure (use when a bucket earns it)

- **Work-area groups.** When a bucket holds several distinct streams, group items under a `### <heading>` with optional `Memory:` / `Repo:` / `Service:` pointer lines beneath the heading. New items go under the matching group; a bucket with no groups just lists items flat.
- **Bold lead-in.** Start an item with a short `**<lead-in>**` when it helps scanning (e.g. `- [ ] **OQ-1 production data feed:** ...`).
- **Sub-bullets.** Nest acceptance criteria or the concrete next sub-step under an item, indented two spaces. The parent stays a one-line index; the sub-bullets carry the checklist. Example:
  ```markdown
  - [ ] **Re-examine RECYCLE_RSS_MB by 2026-05-29 (after the next batch).** (due 2026-05-29)
    - Did oomKilled / 2Gi events stop?
    - What does idle rss settle to between jobs?
  ```
- **Due dates.** When writing, append `(due YYYY-MM-DD)` to an item line (machine-greppable; keep it even when a bold lead-in restates the date in prose). A condition with no fixed date stays in the prose ("after the next batch"); add `(due ...)` only once a real date exists. Flagging recognizes three forms: the canonical `(due ...)` suffix plus prose `Due YYYY-MM-DD` and `by YYYY-MM-DD`, both anchored on the keyword, so incidental dates like "shipped 2026-05-27" are not treated as deadlines. Curated files that predate the suffix still surface as overdue without being rewritten.

### Pinned next-session marker

An optional pin block sits right after the maintenance-rule line, before "State buckets":

```markdown
## >>> NEXT SESSION: start here <<<

<the block, in the shape below>
```

Only one pin per file. Pinning replaces the block; unpinning removes it. (If a file's existing header uses an em dash, leave its exact text alone when editing that file. New pins use the colon form above to stay within the no-em-dash rule.)

#### Write it for the user after a week away

This block is the first thing the next session reads, and the first thing the user reads when they sit back down. They did not write it, they have been away, and they read it in a hurry. Write it to a colleague who walked in five minutes ago, never to the session that just ended.

- **The words.** Strip commit hashes, PR and issue numbers, phase and step numbers, run ids, the names of your own skills, agents, commands and hooks, and harness jargon such as gate, verdict, routed, vacuous, mutation and blast radius. Delete a jargon word rather than define it. Name the subject: "the deploy check reads the wrong commit", not "it was routed". Keep a file path only where the user has to open it, and then put the path alone on its line. One thing is NOT covered by this rule: a command the user has to type. A slash command or a shell line in the fenced block is the answer, not internal vocabulary. What the rule bans is naming the machinery that produced the finding.
- **The shape.** Lead with the one concrete thing to do, give one sentence of why, then the exact command in a fenced block.

**The shape, in this order and nothing else:**

````markdown
<the blocking fact, one line, alone, ONLY if something is built but not in front of the user>

**Do this next: <the one concrete thing, in plain words>.**

<One or two sentences: why this one, and what it releases.>

```sh
<the first command, exactly as it must be typed>
```

**Before you start:** <the one thing that would waste the user's time if they did not know it. Delete this line when there is nothing.>

**Checked:** <what you actually RAN to establish the claims above, or the word "nothing".>
````

**Twelve lines or fewer, not counting the `Checked:` line.** The budget is the specification, not a preference. The provenance line is exempt because it is a stamp rather than prose to read, and making it compete with the account is how it would get dropped. A pin that runs long stops being read, and an unread pin is worse than none because every future session still pays to load it.

**One action per pin.** A pin holding two actions has handed the ranking back to the user, which is the failure the whole block exists to prevent. Runners-up belong in the Active bucket, where they already are.

**Plain must not become rosier.** Every caveat, limit and unknown in the technical account survives into the pin. "The tests pass, and they do not cover the Hebrew rendering" is one line and it is the honest one. A pin written at the end of a session naturally sounds tidier than the session was, so re-read it once against what actually happened.

**The blocking fact goes first, on its own line, above everything.** Not committed, not pushed, not deployed, not merged, behind a flag, local only, waiting on a person. A tidy pin reads as "it works", so a warning placed after the account does not land.

**When the next step is a decision rather than work,** the shape does not change, but the fenced block holds the QUESTION instead of a command, written so it can be answered in one word, plus your recommended answer. A decision handed over as an open question moves the work to the user.

**The `Checked:` line is required, and "nothing" is a real answer.** A pin is written when nothing is running any more, and it is read by someone who acts on it immediately, so a cause, a fix or a predicted state written there gets treated as measured whether or not anybody measured it. The line says which it was: `**Checked:** ran the suite, 426 pass, and read the live commit`, or `**Checked:** nothing. This is reasoned from the error message, not executed`. **Answering "nothing" is not a failure and must never be dressed up.** It is the answer that tells the next session to verify before acting, which is the whole point. Write the command that settles it wherever one exists, so the next session spends one command rather than re-deriving the question.

Why it is a required line rather than a matter of judgement: a pin that states a fix or a state nobody ran gets believed, because the reader acts on it at once. A written rule against that does not fire at the moment the pin is written. A line that must be present does.

#### The same pin, before and after

Written for the session that just ended:

```markdown
## THE ACTION: rebase part 2 onto the new main, then run its review

**PART 1 IS MERGED AND LIVE.** PR #12 squash-merged as `abc1234`, verdict `CLEAN @ def5678`
matching the PR head exactly at the gate. The deploy is live at `abc1234`. It changes nothing
that runs: `NEW_MODE` defaults to `off`.

**PART 2 IS BUILT, GREEN AND OPEN AS PR #13.** Full suite clean; mutation sweep 40 killed
of 42. code-reviewer returned 1 Critical and 4 Warnings, and the user has not chosen what
to fix. The inertness test sees only the absolute import shape, so a relative import is
invisible to it.
```

Written for the user:

````markdown
**The second batch of work is finished but not shipped. It is waiting on you.**

**Do this next: pick which of the review comments are worth fixing.**

The reviewer found eleven things and rated one of them serious. Nothing is fixed yet and
no file has been touched, so the whole batch is sitting still until you choose.

```text
Take the serious one plus three of the four smaller ones? (yes / no / which)
My answer: yes. The fourth is already written and only needs pushing.
```

**Before you start:** the serious one is real. The check that proves this code cannot run
by accident only recognises one of the two ways a file can import it, and 23 files use the
other way. So the check passes without having looked.
````

The second is longer in characters and shorter to read, which is the point. Length was never the problem; vocabulary was.

## Full per-project template (seeded)

```markdown
# <Project> — TODO

Per-project todo list. Synthesized <DATE> from this project's `CLAUDE.md`. Cross-linked from the global cross-project TODO at `~/.claude/projects/<index-dir>/TODO.md`.

Maintenance rule: when state moves, update this file AND the project `CLAUDE.md` (and the cross-project index) in the same turn.

State buckets (in order of relevance):
1. **Active — concrete next steps now**
2. **Queued — agreed, awaiting the user's go-ahead**
3. **Parked / on hold — don't propose unsolicited**
4. **Live (monitor only) — no action unless something breaks**
5. **Advisory — delivered, dormant unless re-engaged**

---

## 1. Active — concrete next steps now

- [ ] <item>

## 2. Queued — agreed, awaiting go-ahead (do not start unsolicited)

## 3. Parked / on hold — don't propose unsolicited

## 4. Live (monitor only) — no action unless something breaks

## 5. Advisory — delivered, dormant unless re-engaged

---

## How to keep this file useful

- When you finish an item, strike it (don't delete on first pass, keep one session of history) and update the matching note in `CLAUDE.md`.
- When the user says "let's pick up X", move X to Active and write the first concrete next step.
- When state shifts, update this file AND the relevant `CLAUDE.md` entry AND the cross-project index in the same turn.
- Don't duplicate detail from `CLAUDE.md` here. One line per item plus a pointer is the target.
```

## Empty template (no CLAUDE.md to seed from)

Same as above, but the synthesis line reads `Created <DATE> as a blank project todo list.` and every bucket is empty (no items under Active).

## Auto-sync rule

Any change to a per-project TODO.md happens in the same turn as the matching updates to the two other artifacts:

1. **Per-project TODO.md** — the edit itself.
2. **Cross-project index** (`~/.claude/projects/<index-dir>/TODO.md`): update the one-line entry for the project (a new Active item, or a status change that moves the project between buckets). One line plus the memory link; never copy the detail.
3. **Memory**: resolve the file with the `find` above rather than naming a store, then update its open-items / pending hook. If no memory file exists for the project, do NOT fabricate one; note that in the report and leave the link out (the index already does this for memory-less projects).
