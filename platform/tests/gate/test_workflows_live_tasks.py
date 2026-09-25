"""SC-6: a live session's `tasks/` is never replaced by a link — empty or not.

The harness notes that directory before SessionStart fires and refuses every
command's output once it finds it linked. The first version held back only a
populated one; an empty one linked from the hook broke a new session on
2026-09-25 (docs/SESSION-CONTAINMENT.md §5).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pf import workflows


def _layout(tmp_path: Path) -> tuple[Path, Path, Path]:
    root, home, sess = tmp_path / "repo", tmp_path / "home", tmp_path / "tmproot" / "sess"
    for d in (root, home, sess):
        d.mkdir(parents=True)
    return root, home, sess


def _link_tasks(root: Path, home: Path, sess: Path, *, live: bool) -> workflows.LinkReport:
    return workflows._link_one(
        "tasks",
        sess / "tasks",
        root / workflows.SCRATCH_DIR / sess.name / "tasks",
        root,
        home,
        sess,
        adopt=True,
        dry_run=False,
        live=live,
        quiet_for=0.0,
        log=None,
    )


@pytest.mark.parametrize("contents", ["missing", "empty", "populated"])
def test_live_tasks_is_left_in_place(tmp_path: Path, contents: str) -> None:
    root, home, sess = _layout(tmp_path)
    tasks = sess / "tasks"
    if contents != "missing":
        tasks.mkdir()
    if contents == "populated":
        (tasks / "b1.output").write_text("x")

    rep = _link_tasks(root, home, sess, live=True)

    assert rep.state == "refused"
    assert not tasks.is_symlink()
    assert tasks.is_dir() == (contents != "missing")


def test_tasks_is_linked_when_not_live(tmp_path: Path) -> None:
    root, home, sess = _layout(tmp_path)
    (sess / "tasks").mkdir()

    rep = _link_tasks(root, home, sess, live=False)

    assert rep.state == "created"
    assert (sess / "tasks").is_symlink()
