# Release and deploy: two stages, never a raw `git push` to main

Shipping goes through two verbs. Both are skills in the companion pack **claude-release-workflow** (install it next to this one):

- **`/pr-checkpoint`** while iterating on a feature branch. It opens a draft pull request and rebuilds the local Docker container so you can test the branch on localhost. It does not merge and does not touch production.
- **`/release`** to ship. It detects PR mode (merge the open pull requests into main) or trunk mode (commit straight to main), updates README.md and the project notes, pushes to every remote, checks the automatic deploy, and rebuilds the local container so localhost matches production.

Rules that go with them:

- **Never push straight to main by hand.** The same pack ships a `block-git-push-main` hook that refuses it.
- **After a deploy, check the commit the live service runs, not only its status.** A platform can report `live` while still serving the previous commit because a webhook missed the push. Compare the deployed commit with the one you pushed, and trigger the deploy by hand if they differ.
- **When a repository has more than one remote, compare every remote's live ref after the push** (`git ls-remote <remote> refs/heads/main`), not the local remote-tracking branch. A mirror remote can fall behind with no error.
- **A green test suite describes the working tree, not what you staged.** After committing and before pushing, compare the committed file with the working copy (`git show HEAD:<file>` against the file on disk).
