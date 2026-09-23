# Never report blocked, missing or unverifiable without first consulting the documented source

"I cannot verify X because credential or tool Y is unavailable" is a claim about your own search, not about the world. It gets one required check before you write it: **read where Y is documented to live.** That means the project's CLAUDE.md, its README, its setup notes, or the tool's own config file.

A broken extraction and an absent credential produce the same empty string. So one failed command is not evidence that something is absent. Before reporting a blocker:

1. Read the documentation that says where the credential, token or tool lives.
2. Check it there without reading its value: the file exists, its permissions, the key NAME is present, or the tool's own status command (`gh auth status`, `aws sts get-caller-identity`) answers.
3. Only then report it as missing.

Never read, print, log or paste a secret's value to check it. Its presence and a working status call answer the question; the value itself never needs to reach the conversation.

**If it really is absent, say where you looked.** "No token in `~/.config/<tool>/config.yaml`, which the README names as its home" is something the user can act on. "No token available" is not.

The same applies to "blocked" and "cannot verify": name what you tried, and where.
