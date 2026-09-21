---
name: concurrent-sessions-revert-tree
description: Multiple Claude sessions run in this one checkout and bulk-discard each other's uncommitted work
type: project
status: active
agent: claude-code
---

This checkout is worked by several Claude CLI sessions at once (three live on
2026-09-20, two of them ~25h old). On 2026-09-20 at 17:01:37 one of them
discarded tracked modifications across the whole tree — dirty paths went 91 → 43,
wiping edits to `.gitmodules`, `platform/src/pf/vendor/registry.yaml`,
`.github/workflows/ai-governance.yml`, `graphify-out/*`, `groups/*/kg/*` and the
deleted `transform/tests/expectations/*.sql`. Nothing was committed, so it was a
bulk `git restore`/`checkout`, not a rebase. Untracked files survived.

**Why:** an hour of work vanished mid-session with no warning, and a re-read of
the files was the only thing that caught it.
**How to apply:** treat uncommitted work here as volatile. Re-read files before
claiming an edit landed, keep a `git diff` patch in the scratchpad, and get
changes onto a branch early. To commit without disturbing another session's
dirty tree, build the commit with plumbing (`read-tree` into a temp
`GIT_INDEX_FILE`, `hash-object`, `write-tree`, `commit-tree`, `git branch`) —
it never touches the working tree, but it skips the `.git/hooks/pre-commit`
gate, so run `uv run pf gate --paths "a,b,c"` by hand. See
[[uv-workspace-hook-deadlock]].
