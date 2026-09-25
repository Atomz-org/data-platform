"""The environment to run git in from a subdirectory, whoever called us.

Git exports `GIT_DIR` to the hooks it runs, and in a linked worktree that is
an absolute path with no `GIT_WORK_TREE` beside it. Git then takes the current
directory as the top of the work tree, so `git ls-files -- .` run from
`groups/<g>/` answers as if that directory were the repository root: the paths
it lists are the right files named relative to the wrong place, and every
caller that joins them back onto its base finds nothing tracked.

That turned the pre-commit gate's harness-map check into a false "stale" in
every worktree — `pf harness` said current, the same gate run by hand passed,
and only `git commit` failed. Dropping the two variables lets git discover the
repository from the directory it is run in, which is what a caller that sets
`cwd` means. `GIT_INDEX_FILE` is kept, made absolute: during `git commit -a`
it names the index actually being committed, and that is the one to read.
"""

from __future__ import annotations

import os
from pathlib import Path


def git_env() -> dict[str, str]:
    """`os.environ` with the repository left for git to discover from `cwd`."""
    env = {k: v for k, v in os.environ.items() if k not in ("GIT_DIR", "GIT_WORK_TREE")}
    index = env.get("GIT_INDEX_FILE")
    if index and not Path(index).is_absolute():
        env["GIT_INDEX_FILE"] = str(Path(index).absolute())
    return env
