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

**A new module path can already be taken.** On 2026-09-22 a session created
`platform/src/pf/harness.py` from an `ls` taken minutes earlier; a sibling
session had committed a different `pf.harness` in between, and the Write
replaced it without a word. `git status` shows the damage as a plain ` M`.
Before creating a file, run `git log -1 -- <path>` and `git status --short
<path>`; if either answers, pick another name (`pf.harnessmap` beside
`pf.harness`) and restore theirs with `git checkout HEAD -- <path>`. Message
the sibling (`ListAgents`, then `SendMessage`) and agree on anchored edits —
never whole-file writes — for any file both hold dirty. Do not `git add` new
files while the sibling is busy: a plain `git commit` on their side sweeps the
whole index. Generated per-scope files (`HARNESS.md`, `kg/architecture.md`)
count only once tracked, so stage them before `pf arch --all` or the maps
render the row as a gap.
