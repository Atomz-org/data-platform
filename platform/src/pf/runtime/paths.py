"""Where a project's Python is found, and the group code it may share.

Project packages are not installed into the environment: a sister is found by
path — `<project>/src` — by its seed script and by the Dagster code location's
`working_directory`. A group may ship Python the same way, at
`groups/<group>/shared/python/src`, for what every sister needs and no sister
owns (connectors, the conformed catalog loader). This module is the one place
that knows both paths, so a project never spells the group's out itself.

Not a workspace member on purpose. A `groups/*/shared/python` glob in the root
workspace bricks every `uv run` hook the moment a branch without the file is
checked out while the directory lingers (`__pycache__` is enough), and that
failure blocks the very tools needed to repair it.
"""

from __future__ import annotations

import sys
from pathlib import Path


def group_dir(project_dir: Path) -> Path:
    """`groups/<group>` for a `groups/<group>/projects/<project>` directory."""
    return Path(project_dir).resolve().parents[1]


def import_paths(project_dir: str | Path) -> list[Path]:
    """The project's `src`, then the group's shared `src` if the group ships one."""
    project_dir = Path(project_dir).resolve()
    paths = [project_dir / "src"]
    shared = group_dir(project_dir) / "shared" / "python" / "src"
    if shared.is_dir():
        paths.append(shared)
    return paths


def extend_sys_path(project_dir: str | Path) -> list[Path]:
    """Put `import_paths` at the front of `sys.path`, once each. Returns what was added."""
    added: list[Path] = []
    for p in reversed(import_paths(project_dir)):
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))
            added.append(p)
    return added
