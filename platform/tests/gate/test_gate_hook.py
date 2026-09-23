"""Installing the gate's hooks.

Two of them, and "is it installed" is not a question about developer
convenience for either. Without `pre-commit` nothing judges a commit before it
is made. Without `pre-push` nothing re-measures one that was made with
`--no-verify`, or made in a checkout that had no hooks at all — and git does
not clone `.git/hooks`, so that is the state every clone starts in. The
question went unasked for the whole life of this repo, `just hooks` was never
run, and a 21-file commit landed unchecked.

CI now re-applies the file cap over a pull request's commits, which is the only
layer a developer's machine cannot skip (`test_gate_commits.py`). These pin the
layers before it: the states that matter, the checkouts where installation used
to fail silently, and — most importantly — the refusal, because an installer
that overwrote someone's own pre-commit script would be a worse failure than
the one it fixes.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest
from conftest import REPO_ROOT
from pf.loops.gate import HOOK_SOURCE, HOOK_TARGET, HOOKS, hook_status, hooks_status, install_hook, install_hooks


def _repo(tmp_path: Path, *, git: bool = True) -> Path:
    """A checkout shaped like this one: a git dir and the gate's hook script."""
    if git:
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True,
                       capture_output=True)
    for rel in HOOKS.values():
        src = tmp_path / rel
        src.parent.mkdir(parents=True, exist_ok=True)
        src.write_text("#!/usr/bin/env bash\nexec uv run pf gate --paths \"$@\"\n")
    return tmp_path


# ------------------------------------------------------------------ missing --

def test_a_fresh_checkout_reports_the_gate_as_missing(tmp_path):
    """The state the repo was actually in, unreported, for its whole life."""
    root = _repo(tmp_path)
    state, detail = hook_status(root)
    assert state == "missing"
    assert "does not run on commit" in detail


def test_install_creates_the_hook(tmp_path):
    root = _repo(tmp_path)
    changed, detail = install_hook(root)
    assert changed is True
    assert (root / HOOK_TARGET).is_symlink()
    assert hook_status(root)[0] == "ok"
    assert HOOK_TARGET in detail


def test_the_link_is_relative_so_the_checkout_can_move(tmp_path):
    """An absolute link points at the machine it was installed on.

    Pinned because the failure is invisible: the hook still exists, git still
    runs it, and it silently execs a script in someone else's home directory —
    or nothing at all.
    """
    root = _repo(tmp_path)
    install_hook(root)
    assert not (root / HOOK_TARGET).readlink().is_absolute()


def test_the_hook_script_is_made_executable(tmp_path):
    """git execs the script; a symlink carries no mode of its own."""
    root = _repo(tmp_path)
    (root / HOOK_SOURCE).chmod(0o644)
    install_hook(root)
    assert (root / HOOK_SOURCE).stat().st_mode & 0o111


# --------------------------------------------------------------- idempotent --

def test_installing_twice_changes_nothing_the_second_time(tmp_path):
    root = _repo(tmp_path)
    assert install_hook(root)[0] is True
    changed, detail = install_hook(root)
    assert changed is False
    assert "already installed" in detail
    assert hook_status(root)[0] == "ok"


def test_an_absolute_legacy_link_still_counts_as_installed(tmp_path):
    """`just hooks` and older installs spelled the link differently."""
    root = _repo(tmp_path)
    target = root / HOOK_TARGET
    target.parent.mkdir(parents=True, exist_ok=True)
    target.symlink_to((root / HOOK_SOURCE).resolve())
    assert hook_status(root)[0] == "ok"
    assert install_hook(root)[0] is False


def test_a_regular_file_that_calls_the_gate_counts(tmp_path):
    """Someone chaining our gate into their own script is installed, not foreign."""
    root = _repo(tmp_path)
    target = root / HOOK_TARGET
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("#!/bin/sh\nuv run pf gate --paths \"$1\"\n")
    assert hook_status(root)[0] == "ok"


# ------------------------------------------------------------------ foreign --

def test_a_foreign_hook_is_not_overwritten(tmp_path):
    """The refusal. Destroying someone's pre-commit script to install ours is
    a worse outcome than the gate being absent, because it is unrecoverable."""
    root = _repo(tmp_path)
    target = root / HOOK_TARGET
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("#!/bin/sh\nnpm run lint\n")

    state, _ = hook_status(root)
    assert state == "foreign"

    changed, detail = install_hook(root)
    assert changed is False
    assert "refused" in detail
    assert target.read_text() == "#!/bin/sh\nnpm run lint\n"   # untouched


def test_force_replaces_a_foreign_hook(tmp_path):
    root = _repo(tmp_path)
    target = root / HOOK_TARGET
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("#!/bin/sh\nnpm run lint\n")

    changed, _ = install_hook(root, force=True)
    assert changed is True
    assert hook_status(root)[0] == "ok"


# ------------------------------------------------------------------ no git --

def test_outside_a_git_checkout_it_is_a_no_op_not_an_error(tmp_path):
    """`pf check` runs in places that are not checkouts; this must not fail."""
    root = _repo(tmp_path, git=False)
    assert hook_status(root)[0] == "no-git"
    changed, detail = install_hook(root)
    assert changed is False
    assert "not a git checkout" in detail


def test_a_missing_hook_script_is_reported_not_raised(tmp_path):
    root = _repo(tmp_path)
    (root / HOOK_SOURCE).unlink()
    changed, detail = install_hook(root)
    assert changed is False
    assert "missing" in detail


# ------------------------------------------------------------- end to end --

def test_the_installed_hook_actually_blocks_an_oversized_commit(tmp_path):
    """The whole point: not that a symlink exists, but that git refuses.

    Uses a stub gate script so the test pins the wiring — git finds the hook,
    execs it, and honours a non-zero exit — without depending on the real
    policy file or on `uv` being available in the test environment.
    """
    root = _repo(tmp_path)
    (root / HOOK_SOURCE).write_text(
        "#!/usr/bin/env bash\n"
        "n=$(git diff --cached --name-only | wc -l)\n"
        '[ "$n" -gt 2 ] && { echo "DENY $n files" >&2; exit 1; }\n'
        "exit 0\n")
    install_hook(root)

    def git(*a, **kw):
        return subprocess.run(["git", *a], cwd=root, capture_output=True,
                              text=True, **kw)

    git("config", "user.email", "t@example.com")
    git("config", "user.name", "t")

    for i in range(3):
        (root / f"f{i}.txt").write_text("x")
    git("add", "-A")
    out = git("commit", "-m", "too many files")
    # Assert on the refusal, not on the count: `git add -A` also stages the hook
    # script itself, and `wc -l` pads its output. Pinning "3 files" would make
    # this fail on formatting while the behaviour under test was correct.
    assert out.returncode != 0, "the hook did not block the commit"
    assert "DENY" in (out.stderr + out.stdout)
    assert not git("log", "--oneline").stdout.strip(), "a commit landed anyway"


# ------------------------------------------------------- CLI self-healing --
#
# The glue that closes the gap `pf check` alone cannot: reporting a missing hook
# only helps whoever runs `pf check`, and the person who does not run it is
# exactly the one committing unchecked. Every `pf` command installs it instead.

def test_every_pf_command_installs_the_gate(monkeypatch, tmp_path):
    from pf import cli

    called: list[Path] = []
    monkeypatch.delenv("PF_NO_HOOK_INSTALL", raising=False)
    monkeypatch.setattr(cli, "root", lambda: tmp_path)
    monkeypatch.setattr("pf.loops.gate.install_hooks",
                        lambda r, **kw: (called.append(r) or []))
    cli._bootstrap_commit_gate()
    assert called == [tmp_path]


def test_the_opt_out_is_honoured(monkeypatch, tmp_path):
    from pf import cli

    called: list[Path] = []
    monkeypatch.setenv("PF_NO_HOOK_INSTALL", "1")
    monkeypatch.setattr(cli, "root", lambda: tmp_path)
    monkeypatch.setattr("pf.loops.gate.install_hooks",
                        lambda r, **kw: (called.append(r) or []))
    cli._bootstrap_commit_gate()
    assert called == []


def test_an_install_failure_never_blocks_the_real_command(monkeypatch, tmp_path):
    """A repo you cannot write a hook into must still let you run `pf`."""
    from pf import cli

    monkeypatch.delenv("PF_NO_HOOK_INSTALL", raising=False)
    monkeypatch.setattr(cli, "root", lambda: tmp_path)

    def boom(*a, **kw):
        raise OSError("read-only filesystem")

    monkeypatch.setattr("pf.loops.gate.install_hooks", boom)
    cli._bootstrap_commit_gate()      # must not raise


# ------------------------------------------------------------- both of them --
#
# The pre-commit hook is skippable, and skipping it leaves no trace. The pre-push
# hook is the layer that notices before the change leaves the machine, so it is
# installed by the same command, in the same breath, or it is the control that
# exists in a file and nowhere else.

def test_both_hooks_are_installed_together(tmp_path):
    root = _repo(tmp_path)
    installed = {hook: changed for hook, changed, _ in install_hooks(root)}
    assert installed == {"pre-commit": True, "pre-push": True}
    assert [state for _, state, _ in hooks_status(root)] == ["ok", "ok"]


def test_a_missing_pre_push_says_what_it_is_for(tmp_path):
    """A hook whose purpose nobody can state is a hook nobody reinstalls."""
    root = _repo(tmp_path)
    state, detail = hook_status(root, "pre-push")
    assert state == "missing"
    assert "--no-verify" in detail


def test_one_refusal_does_not_stop_the_other_hook(tmp_path):
    """A chained pre-commit and no pre-push is a real checkout, and the half
    that can be fixed should be."""
    root = _repo(tmp_path)
    target = root / HOOK_TARGET
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("#!/bin/sh\necho mine\n")

    outcome = {hook: changed for hook, changed, _ in install_hooks(root)}
    assert outcome == {"pre-commit": False, "pre-push": True}
    assert hook_status(root, "pre-commit")[0] == "foreign"
    assert hook_status(root, "pre-push")[0] == "ok"


def test_each_hook_calls_the_gate_it_is_named_for():
    """The wiring, in this repository: one asks about a staged set, the other
    about the commits that set became."""
    assert "pf gate --paths" in (REPO_ROOT / HOOKS["pre-commit"]).read_text(encoding="utf-8")
    assert "pf gate --commits" in (REPO_ROOT / HOOKS["pre-push"]).read_text(encoding="utf-8")


# ------------------------------------------------- checkouts it used to miss --

def test_a_worktree_installs_into_the_hooks_directory_git_actually_uses(tmp_path):
    """`.git` is a *file* in a linked worktree.

    Assuming `.git/hooks` there raises NotADirectoryError, which `pf bootstrap`
    swallowed — so every worktree ran with no gate while reporting nothing. A
    worktree is also where an agent is most likely to be working.
    """
    (tmp_path / "main").mkdir()
    main = _repo(tmp_path / "main")
    subprocess.run(["git", "add", "-A"], cwd=main, check=True, capture_output=True)
    subprocess.run(["git", "-c", "user.email=g@x", "-c", "user.name=g", "commit", "-qm", "hooks"],
                   cwd=main, check=True, capture_output=True)
    linked = tmp_path / "linked"
    subprocess.run(["git", "worktree", "add", "-q", str(linked), "-b", "side"],
                   cwd=main, check=True, capture_output=True)

    changed, detail = install_hook(linked)
    assert changed is True, detail
    # Git shares one hooks directory across every worktree, so it lands in the
    # main checkout's — and the worktree must still read it as installed.
    assert (main / HOOK_TARGET).is_symlink()
    assert hook_status(linked)[0] == "ok"
    assert hook_status(main)[0] == "ok"


def test_a_link_to_a_file_that_is_gone_is_replaced_not_refused(tmp_path):
    """A dead link is an empty slot that reads as occupied.

    Calling it foreign would refuse to install over it — permanently, to
    protect a script that is not there.
    """
    root = _repo(tmp_path)
    target = root / HOOK_TARGET
    target.parent.mkdir(parents=True, exist_ok=True)
    target.symlink_to("../../gone/pre_commit.sh")

    assert hook_status(root)[0] == "missing"
    changed, _ = install_hook(root)
    assert changed is True
    assert hook_status(root)[0] == "ok"


# ------------------------------- the hooks directory belongs to the repo -----
#
# Git keeps ONE hooks directory per repository and every worktree execs it. That
# makes "which checkout did the install" the wrong thing for a link to depend
# on, and it broke exactly there: a worktree on a branch that added
# `pre_push.sh` installed the hook into the main checkout, whose branch predated
# the script — so every `git push` from the main checkout ran a hook calling
# `pf gate --commits` that its own `pf` had never heard of, and died on a usage
# error until the link was deleted by hand.

def test_the_link_never_points_into_the_checkout_that_ran_the_install(tmp_path):
    (tmp_path / "main").mkdir()
    main = _repo(tmp_path / "main")
    # The owner's branch predates the pre-push script.
    (main / HOOKS["pre-push"]).unlink()
    subprocess.run(["git", "add", "-A"], cwd=main, check=True, capture_output=True)
    subprocess.run(["git", "-c", "user.email=g@x", "-c", "user.name=g", "commit", "-qm", "hooks"],
                   cwd=main, check=True, capture_output=True)
    linked = tmp_path / "linked"
    subprocess.run(["git", "worktree", "add", "-q", str(linked), "-b", "side"],
                   cwd=main, check=True, capture_output=True)
    # ...and the worktree, on a later branch, does have it.
    src = linked / HOOKS["pre-push"]
    src.parent.mkdir(parents=True, exist_ok=True)
    src.write_text("#!/usr/bin/env bash\nexec uv run pf gate --commits \"$@\"\n")

    install_hook(linked, hook="pre-push")

    link = (main / ".git" / "hooks" / "pre-push").readlink()
    assert str(linked) not in str(link), f"the link reaches into a worktree: {link}"
    assert str(link) == "../../platform/hooks/pre_push.sh"


def test_a_hook_the_owner_cannot_serve_yet_is_dormant_rather_than_broken(tmp_path):
    """Pointing at a file that is not there is the right answer, not a bug.

    Git skips a hook it cannot execute, so the push works and the link starts
    working by itself the moment that checkout has the script. The status says
    `missing`, which is what it is — the alternative, refusing to install,
    leaves the same checkout ungated forever with an extra manual step.
    """
    root = _repo(tmp_path)
    (root / HOOKS["pre-push"]).unlink()
    target = root / ".git" / "hooks" / "pre-push"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.symlink_to("../../platform/hooks/pre_push.sh")

    assert hook_status(root, "pre-push")[0] == "missing"


# --------------------------------------------- the hook, against a stub pf ---

@pytest.mark.parametrize(("pf_exit", "hook_exit", "says"), [
    (0, 0, ""),
    (2, 0, "has no 'gate --commits'"),
    (1, 1, ""),
])
def test_the_pre_push_hook_blocks_a_denial_and_stands_aside_for_an_older_pf(
    tmp_path, pf_exit, hook_exit, says,
):
    """Exit 2 is typer's usage error, and here it can only mean one thing: the
    `pf` in this checkout has no `--commits`. Every worktree shares one hooks
    directory, so an older branch can end up running a newer checkout's hook.
    Blocking its push over a flag its author cannot add is worse than saying so
    and standing aside — CI still applies the cap on the pull request."""
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True, capture_output=True)
    stub = tmp_path / "bin"
    stub.mkdir()
    (stub / "uv").write_text(f"#!/bin/sh\nexit {pf_exit}\n")
    (stub / "uv").chmod(0o755)

    proc = subprocess.run(
        ["bash", str(REPO_ROOT / HOOKS["pre-push"])],
        cwd=tmp_path,
        input="refs/heads/x 1111111111111111111111111111111111111111 refs/heads/x " + "0" * 40 + "\n",
        capture_output=True, text=True,
        env={**os.environ, "PATH": f"{stub}:{os.environ['PATH']}"},
    )
    assert proc.returncode == hook_exit, proc.stderr
    if says:
        assert says in proc.stderr
