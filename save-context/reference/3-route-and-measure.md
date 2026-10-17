Two things decide where a discovery goes: what kind it is, and how much room the destination has. Do both now, because a measurement can change the destination.

**Measure first.**

```sh
wc -c ~/.claude/CLAUDE.md
wc -c ~/.claude/projects/<X>/CLAUDE.md
wc -l -c ~/.claude/projects/<X>/memory/MEMORY.md
```

The limits: the global file at the size target you keep for it; a project notes file at the threshold that project's own file states, which differs per project, so read it there; the memory index at 200 lines and 25KB, which the loader truncates in silence.

**A file already over its limit does not get another line from this save.** Put the content in the matching satellite, and say in the report that the file is over and `/split-claude-md` is due on it.

**Then route.** Most specific destination that still fits, and never the same rule in two places:

- **Nothing the repository already answers.** A directory layout, a dependency list, an architecture the code states plainly. Do not write it anywhere.
- **A rule about how Claude should behave on this project**: the project notes file.
- **A build, test, run or deploy command, or a code convention**: the repo file, so a session launched in the repo gets it.
- **A rule that applies everywhere**: the global file, as ONE line, with the evidence in a satellite file beside it, one per topic (testing, deployment, a given SDK). Keep the rule always loaded and move only its dated evidence. Never put both halves in an always-loaded file.
- **A rule that fires on a file type rather than on a conversation**: a rule file in `.claude/rules/` with `paths:` frontmatter. It leaves the always-loaded set entirely, which is the cheapest destination there is. It is lost after a compaction until a matching file is read again, so send a rule here only when a file triggers it.
- **A multi-step procedure**: a skill, not a rule. Anything with an order of operations belongs in a body that loads when it is needed.
- **An observational fact about a system**: memory. If you split the memory index into topic indexes, file the row in the matching one. Only a fact that fires on any task belongs in `MEMORY.md` itself.
- **Project state**: always memory, never a CLAUDE.md.
- **An external pointer**, meaning a board, a dashboard or a service id: a memory `reference_*` entry.

The ownership test in one line: a rule about how to behave goes to a CLAUDE.md, a fact about a system goes to memory, and neither file repeats the other.
