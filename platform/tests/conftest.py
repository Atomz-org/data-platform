"""Shared test setup — and the single definition of where the repository is.

Six test files each computed the repo root as `Path(__file__).parents[2]`. That
is a magic number describing how deep the file happens to sit, and it was
silently wrong the moment these tests moved into subdirectories: `parents[2]`
stopped being the checkout and started being `platform/`, so every path built
from it pointed at a directory that does not exist. Nothing said so — the tests
failed as "file not found" on paths nobody had changed.

Walking up for the marker directories instead is depth-independent, so the next
reorganisation cannot break it, and there is one definition to correct rather
than six copies to find. This is the same rule `pf.kg.build._repo_root` and
`pf.obs.repo_root` already follow, for the same reason.

Resolved from `__file__` rather than from the working directory on purpose: a
test's location is a fact, and cwd is whatever the runner happened to be in.
"""

from __future__ import annotations

from pathlib import Path

import pytest

#: Directories that only ever appear together at the top of this repository.
MARKERS = ("platform", "groups")


def _find_repo_root() -> Path:
    for candidate in Path(__file__).resolve().parents:
        if all((candidate / m).is_dir() for m in MARKERS):
            return candidate
    raise RuntimeError(
        f"no repository root above {__file__}: expected a directory holding "
        f"{' and '.join(MARKERS)}/"
    )


#: The checkout root. Import it directly for module-level constants —
#: `from conftest import REPO_ROOT` — or take the `repo_root` fixture in a test.
REPO_ROOT = _find_repo_root()


@pytest.fixture(scope="session")
def repo_root() -> Path:
    """The checkout root, for tests that would rather take it than import it."""
    return REPO_ROOT
