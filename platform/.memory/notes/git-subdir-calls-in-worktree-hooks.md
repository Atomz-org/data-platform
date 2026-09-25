---
name: git-subdir-calls-in-worktree-hooks
description: git run from a subdirectory inside a worktree's hook lists the wrong paths — pass env=pf.gitenv.git_env()
type: feedback
status: resolved
agent: claude-code
---

Git exports GIT_DIR (absolute, no GIT_WORK_TREE) to hooks in a linked worktree, so `git ls-files -- .` with cwd=<subdir> treats that subdir as the repo root. The pre-commit gate's harness_required check rendered every HARNESS.md differently inside `git commit` than `pf harness` did, and denied every commit made from a worktree as stale. **How to apply:** any subprocess git call whose cwd is not the repo root passes env=git_env(); calls run from the root are unaffected.
