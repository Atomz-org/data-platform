---
name: uv-workspace-hook-deadlock
description: Checking out a branch without groups/commodity/projects/commodity-india/pyproject.toml bricks every Bash/Write/Edit call via the uv-run hooks
type: project
status: active
---

`.claude/settings.json` runs PreToolUse and PostToolUse hooks as `uv run --project "$CLAUDE_PROJECT_DIR" ...` on Edit|Write|MultiEdit|NotebookEdit|Bash. The root pyproject.toml workspace glob is `groups/*/projects/*`. The commodity-india project's pyproject.toml is tracked only on the commodity-stack/* branches; on any other branch its ignored build output (reporting/build) stays on disk, uv refuses to resolve the workspace, every hook errors, and every mutating tool is blocked — including Write, so the session cannot repair itself. Subagents and worktrees hit the same hook (CLAUDE_PROJECT_DIR is pinned to the primary checkout).

As of 2026-09-20 `groups/commodity/projects/commodity-india/pyproject.toml` is
tracked on `main` as well, so a checkout of or a worktree from `main` resolves
on its own and the placeholder is no longer what is holding this up there. The
hazard stands for any branch that still lacks the file.

On 2026-09-19 the user created an untracked placeholder `groups/commodity/projects/commodity-india/pyproject.toml` (name `commodity-india-placeholder`) to prevent this.

**Why:** the deadlock cost most of a session and needed the user to run a command by hand three times.
**How to apply:** before any `git checkout` in this repo, confirm the placeholder (or the real file) exists. Never `git add` the placeholder. When checking out commodity-stack/*, git will refuse to overwrite it — remove it first. See [[pr-merge-classifier-limits]].
