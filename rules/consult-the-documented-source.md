# Never report blocked, missing or unverifiable without first consulting the documented source

"I cannot verify X because credential or tool Y is unavailable" is a claim about your own search, not about the world. It gets one required check before you write it: **read where Y is documented to live.** That means the project's CLAUDE.md, its README, its setup notes, or the tool's own config file.

A broken extraction and an absent credential produce the same empty string. So one failed command is not evidence that something is absent. Before reporting a blocker:

1. Read the place the project says the credential, token or tool lives.
2. Try reading it there, the documented way.
3. Only then report it as missing.

**If it really is absent, say where you looked.** "No token in `~/.config/<tool>/config.yaml`, which the README names as its home" is something the user can act on. "No token available" is not.

The same applies to "blocked" and "cannot verify": name what you tried, and where.
