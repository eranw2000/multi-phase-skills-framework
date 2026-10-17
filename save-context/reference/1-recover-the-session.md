A long session compacts, and compaction replaces the conversation with a summary. Instructions come back from disk; the conversation does not. So on the sessions that most need saving, "review the conversation" reads a retelling, and the specifics this save exists to rescue are the first thing a summary drops.

The transcript on disk is complete whether or not that happened. Read it rather than your own recall. It is a `.jsonl` file with one JSON object per line and is often large, so read it in pieces or hand it to a subagent rather than loading it whole.

**IDENTIFY the transcript, do not take the newest.** `ls -t ~/.claude/projects/*/*.jsonl | head -1` reads across EVERY project, so it hands you whichever session on this machine wrote last, which is routinely a parallel session in another repository. A save built on a stranger's transcript is worse than a save built on your own recall, because it reads as evidence. In order:

1. **The session's own path**, when a hook envelope or the caller gave it. That is the only answer with no guess in it. Read that file.
2. **Otherwise list the candidates under THIS project's encoded directory only**, newest first, and ask which one, naming your best guess as the recommendation:

```sh
CWD="<the project launch directory>"
ls -lt "$HOME/.claude/projects/$(printf '%s' "$CWD" | tr -c 'A-Za-z0-9' '-')"/*.jsonl
```

3. **When there is no one to ask, stop and report `no transcript identity`** with the candidates you saw, rather than picking one. A save is the record of what happened, so a wrong source is a wrong record that the next session trusts.

Never widen the glob back to `projects/*/` to find "a" transcript. One match in the project directory is the answer; none means this directory is not where the session ran, which is a fact to report.

Say in the final report which source you reviewed, the transcript or the live context. A save built on a summary is worth less, and the reader is entitled to know which one they got.
