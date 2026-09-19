"""Installing the commit gate.

The gate is enforced at commit time and nowhere else — CI does not re-apply
`maxFiles` or the staged-set denylist. So "is the hook installed" is not a
question about developer convenience; it is the question of whether the gate
runs at all. It went unasked for the whole life of the repo, `just hooks` was
never run, and a 21-file commit landed unchecked.

These pin the three states that matter and, most importantly, the refusal: an
installer that silently overwrote someone's own pre-commit script would be a
worse failure than the one it fixes.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from pf.loops.gate import HOOK_SOURCE, HOOK_TARGET, hook_status, install_hook


def _repo(tmp_path: Path, *, git: bool = True) -> Path:
    """A checkout shaped like this one: a git dir and the gate's hook script."""
    if git:
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True,
                       capture_output=True)
    src = tmp_path / HOOK_SOURCE
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
    monkeypatch.setattr("pf.loops.gate.install_hook",
                        lambda r, **kw: (called.append(r) or (False, "stub")))
    cli._bootstrap_commit_gate()
    assert called == [tmp_path]


def test_the_opt_out_is_honoured(monkeypatch, tmp_path):
    from pf import cli

    called: list[Path] = []
    monkeypatch.setenv("PF_NO_HOOK_INSTALL", "1")
    monkeypatch.setattr(cli, "root", lambda: tmp_path)
    monkeypatch.setattr("pf.loops.gate.install_hook",
                        lambda r, **kw: (called.append(r) or (False, "stub")))
    cli._bootstrap_commit_gate()
    assert called == []


def test_an_install_failure_never_blocks_the_real_command(monkeypatch, tmp_path):
    """A repo you cannot write a hook into must still let you run `pf`."""
    from pf import cli

    monkeypatch.delenv("PF_NO_HOOK_INSTALL", raising=False)
    monkeypatch.setattr(cli, "root", lambda: tmp_path)

    def boom(*a, **kw):
        raise OSError("read-only filesystem")

    monkeypatch.setattr("pf.loops.gate.install_hook", boom)
    cli._bootstrap_commit_gate()      # must not raise
