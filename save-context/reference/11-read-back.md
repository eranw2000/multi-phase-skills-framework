You have just edited files that every future session reads, and nothing has checked them. This step is short and it is not optional.

- **Re-read each span you edited.** An edit whose anchor starts mid-sentence duplicates a clause, and the write reports success either way.
- **Re-measure every file you added to**, against the same limits as step 3, and report the figures.
- **GREP for what this session made false; do not rely on noticing it.** "Look harder" is not a check, and this is the expensive kind of miss: the cold-start skills READ these claims and hand them to the user as fact. `new-session` pulls anything under "Deferred", "Next steps" or "TODO" and reports it as live open work; `project-status` reads the file for the deployed service id. So a stale line is not inert, it is amplified into a false answer. Run this and READ every hit:

  ```sh
  STALE='deferred|not deployed|never deployed|to go live|live deploy|no [a-z]+ service|nothing auto-deployed|no live|uncommitted|not pushed|not committed|not running|to ship|planned|still to do|next steps|TODO'
  grep -nEi "$STALE" ~/.claude/projects/<X>/CLAUDE.md

  # Memory files are NOT in one fixed directory: a memory store follows the launch
  # directory. Find every memory file that names the project, PRINT the list, then
  # grep those. An empty list means the name did not match, never that it is clean.
  MEM=$(find ~/.claude/projects -maxdepth 3 -path '*/memory/*.md' -exec grep -liF -- "<X>" {} +)
  echo "$MEM"
  [ -z "$MEM" ] && echo "NO MEMORY FILE NAMES <X> - try another spelling, do NOT read this as clean"
  [ -n "$MEM" ] && printf '%s\n' "$MEM" | while IFS= read -r f; do grep -nEi "$STALE" "$f" /dev/null; done

  grep -nEi "$STALE" ~/.claude/projects/<index-dir>/TODO.md | grep -i "<X>"
  ```

  **The memory file is not in one fixed directory.** A memory store follows the session's
  LAUNCH directory, so a project's memory can sit in any of several stores, and a project
  can have one in TWO stores. A glob that names one store matches nothing for the others,
  zsh prints `no matches found`, and an empty result reads exactly like a clean sweep. On a
  real setup that let a memory file say a pull request was "open, not merged" for five
  weeks after it merged, in a file recalled into OTHER projects' sessions. Print the resolved
  list every time; the print IS the control.

  **Use `find -exec`, never `grep $MEM`.** zsh does NOT word-split an unquoted parameter, so
  a two-file list reaches grep as one filename and the whole check dies with
  `No such file or directory`, which reads like a missing file rather than a broken check.

  **Run it on all three, because the same false claim copies itself across them.** On a real
  project, the notes file, the project memory AND the cross-project index row each
  independently said "deploy deferred" and "3 features still UNCOMMITTED" while the app had
  been live for a week. Fixing only the notes file leaves two artifacts still lying, and the
  memory one is worse, because it is recalled into sessions on other projects.

  Confirm each hit is STILL TRUE, and **rewrite the ones this session falsified rather than adding a new section beside them.** Expect legitimate hits; the check is that you read them, not that the count reaches zero. **Writing the new fact into a NEW file does not discharge this**, and that is the shape to watch for, because creating a thorough document feels like recording the fact. On a real project, a session deployed the app to production and wrote a full handoff document about it, while the notes file beside it went on saying no service existed yet and listing the deploy under "Deferred". A week later the user asked for the production server address and the project's own file answered wrongly.
- **GREP for a figure that moves by itself.** The stale check above matches status WORDS, so it cannot see a NUMBER that goes wrong while the file sits still. A download percentage, a free-disk reading, a days-since count, a live total: each is false within hours and nothing signals it. Run this too, and READ every hit:

  ```sh
  VOLATILE='(at|now|reached) [0-9]+ ?%|[0-9]+ ?% (complete|done|downloaded|uploaded|through|finished|of the way)|[0-9.]+ ?[KMGT]B (of|free|left|remaining)|(days|hours|minutes) (since|left|ago)|last (seen|run|deployed|updated|synced)|as of (today|now)|currently [0-9]|[0-9]+ (open|active|pending|queued|remaining)|already (fetched|downloaded|uploaded|processed)|[0-9]+h[0-9]+m'
  grep -nEi "$VOLATILE" ~/.claude/projects/<X>/CLAUDE.md
  grep -nEi "$VOLATILE" ~/.claude/projects/<X>/*.md
  ```

  **A hit is not a failure, it is a line to read.** Keep the figure only in one of two forms: it carries the moment it was read ("40 GB free, read 2026-08-27 at 22:00 UTC"), or the command that re-reads it sits beside it. Otherwise cut the moving half and keep the durable half: a self-moving figure does not belong in a document that sits still.

  Measured on a real project: a save wrote "at 58%, 8.0 GB of 13 GB, about 1h20m left" into the notes file and "of which 7.6 GB is already fetched" into a second document. Four minutes later the true figures were 62% and 8.5 GB and free disk had dropped a gigabyte, so both sentences were false before the session ended. The stale grep above ran over both files in that same save and reported no hits, because a moving number contains none of its status words. A bare `[0-9]+%` alternative was DROPPED from the pattern after it fired mostly on legitimate accuracy rates, weights and thresholds. The pattern fires on both of those sentences and stays silent on "150 GB/s", "36 GB unified memory" and "precision improved from 70% to 88%".

  **A claim ABOUT another document counts too.** The same save wrote "MODEL_RECOMMENDATION.md records 62 GB free" into the notes file minutes after correcting that very document to say 40. When one save edits two files that describe each other, re-read the describing sentence after the described file changes.
- **These files are edited by parallel sessions.** If a file changed under you between reading and writing, re-read it and re-apply your change. Never rewrite a block from a copy you took earlier in the session.
