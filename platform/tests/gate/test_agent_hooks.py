"""One gate, every harness: the adapters reach the same core and say "no" in
each harness's own dialect.

  parity              the same action gets the same verdict from every harness
                        with an adapter. A tool whose adapter drifted would be
                        gated in name only. Each harness's module adds its
                        payload to `SAMPLES`; the tests below grow with it.

  permissions are     `.claude/settings.json`'s deny/ask lists reach the tools
    a source            that do not read that file, resolved the way Claude
                        resolves them, from the directory holding `.claude/`.

  never fail closed   malformed stdin, an unknown harness, an unknown event —
                        allow, silently.
"""

from __future__ import annotations

import json
import shutil
from collections.abc import Callable
from pathlib import Path

import pytest
from conftest import REPO_ROOT
from pf import agenthook, harness_adapters
from pf.agenthook import BASH, EDIT, READ, WRITE, Call, Rule, bypasses_hooks, command_matches, path_matches
from pf.harness_adapters import patch_paths, run


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A repo shape with the real gate.yaml and permissions, and provenance off."""
    (tmp_path / "platform").mkdir()
    (tmp_path / "groups" / "acme" / "projects" / "acme-eu" / ".claude").mkdir(parents=True)
    (tmp_path / "groups" / "acme" / "ontology").mkdir()
    shutil.copy(REPO_ROOT / "gate.yaml", tmp_path / "gate.yaml")
    (tmp_path / ".claude").mkdir()
    shutil.copy(REPO_ROOT / ".claude" / "settings.json", tmp_path / ".claude" / "settings.json")
    shutil.copy(
        REPO_ROOT / "groups" / "acme" / "projects" / "acme-eu" / ".claude" / "settings.json",
        tmp_path / "groups" / "acme" / "projects" / "acme-eu" / ".claude" / "settings.json",
    )
    monkeypatch.setenv("PF_NOTIFY", "0")
    monkeypatch.delenv("CURSOR_VERSION", raising=False)
    monkeypatch.delenv("CURSOR_PROJECT_DIR", raising=False)
    # Provenance is the real ledger's business; here it must not write one.
    monkeypatch.setattr(agenthook, "_record_execution", lambda *a, **k: None)
    import pf.provenance.ledger as prov

    monkeypatch.setattr(prov, "intent", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("off")))
    return tmp_path


# ------------------------------------------------------------- the payloads --
#: Per harness: (tool, root, target) → what that harness sends for "write
#: `target`" (tool="edit") or "run `target`" (tool="bash"), in its own shape.
SAMPLES: dict[str, Callable[[str, Path, str], dict]] = {
    "claude": lambda tool, root, t: (
        {"tool_name": "Write", "tool_input": {"file_path": str(root / t)}, "cwd": str(root)}
        if tool == "edit"
        else {"tool_name": "Bash", "tool_input": {"command": t}, "cwd": str(root)}
    ),
    # Every Codex edit is an apply_patch, its envelope in `command`.
    "codex": lambda tool, root, t: (
        {
            "hook_event_name": "PreToolUse",
            "tool_name": "apply_patch",
            "tool_input": {"command": f"*** Begin Patch\n*** Add File: {t}\n+x\n*** End Patch\n"},
            "tool_use_id": "call_1",
            "cwd": str(root),
            "session_id": "s",
        }
        if tool == "edit"
        else {"tool_name": "Bash", "tool_input": {"command": t}, "cwd": str(root), "session_id": "s"}
    ),
}

#: Harnesses that prompt a person themselves from generated rules, so their
#: hook stands aside on an `ask` — the rendered rule is checked instead.
NATIVE_ASK = {"codex"}


def denied(out: tuple[str, str, int]) -> bool:
    stdout, _stderr, code = out
    if code == 2:
        return True
    try:
        d = json.loads(stdout or "{}")
    except json.JSONDecodeError:
        return False
    hso = d.get("hookSpecificOutput") or {}
    return (
        d.get("permission") == "deny"
        or d.get("permissionDecision") == "deny"
        or d.get("decision") in ("deny", "block")
        or hso.get("permissionDecision") == "deny"
    )


def test_every_adapter_has_a_sample() -> None:
    """A harness with an adapter and no sample is a harness no test gates."""
    assert set(harness_adapters.ADAPTERS) == set(SAMPLES)


# ------------------------------------------------------------------ parity --
@pytest.mark.parametrize("harness", sorted(SAMPLES))
@pytest.mark.parametrize(
    "tool,target,expect_deny",
    [
        ("edit", ".env", True),  # gate.yaml denylist
        ("edit", "platform/src/pf/x.py", False),
        ("bash", "git commit --no-verify -m x", True),
        ("bash", 'git commit -m "never use --no-verify"', False),
        ("bash", "uv run pytest", False),
    ],
)
def test_every_harness_gets_the_same_verdict(
    repo: Path, harness: str, tool: str, target: str, expect_deny: bool
) -> None:
    out = run(harness, "pre", json.dumps(SAMPLES[harness](tool, repo, target)))
    assert denied(out) is expect_deny, f"{harness}: {out}"


def test_settings_permissions_reach_the_harnesses_that_do_not_read_them(repo: Path) -> None:
    """`Edit(vendor/**)` is in `.claude/settings.json`. Claude applies it
    itself; for everyone else the core does, from the same file."""
    for h in sorted(SAMPLES):
        if h == "claude":
            continue
        out = run(h, "pre", json.dumps(SAMPLES[h]("edit", repo, "vendor/ecc/x.py")))
        assert denied(out), f"{h} wrote under vendor/: {out}"


def test_ask_rules_never_pass_silently(repo: Path) -> None:
    """`Bash(git push:*)` asks a person. A harness that can ask from a hook
    asks; one that cannot refuses; one that prompts natively is handed the
    rule — none lets it through unasked."""
    from pf import harness

    t = harness.targets(repo)
    for h in sorted(SAMPLES):
        if h == "claude":
            continue
        out = run(h, "pre", json.dumps(SAMPLES[h]("bash", repo, "git push origin main")))
        if h in NATIVE_ASK:
            assert out == ("", "", 0), h
            assert any("git push" in body for rel, body in t.items() if f".{h}" in rel or h in rel), h
        else:
            assert '"ask"' in out[0] or denied(out), f"{h} let `git push` through: {out}"


def test_codex_prompts_from_its_own_rules(repo: Path) -> None:
    from pf import harness

    rules = harness.targets(repo)[".codex/rules/pf.rules"]
    assert 'prefix_rule(pattern=["git", "push"], decision="prompt"' in rules


def test_codex_shell_scripts_are_read_as_scripts(repo: Path) -> None:
    """An argv of `["bash", "-lc", "..."]` is one script: the guard must see its words."""
    p = {"tool_name": "Bash", "tool_input": {"command": ["bash", "-lc", "git commit -n -m x"]}, "cwd": str(repo)}
    assert denied(run("codex", "pre", json.dumps(p)))


def test_codex_is_named_in_memory(monkeypatch: pytest.MonkeyPatch) -> None:
    from pf.memory import detect_agent

    for k in ("PF_AGENT", "CLAUDECODE", "GEMINI_CLI"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("CODEX_THREAD_ID", "t")
    assert detect_agent() == "codex"


def test_claude_is_left_to_its_own_permission_lists(repo: Path) -> None:
    """Claude Code applies `.claude/settings.json` itself; answering for it
    here would prompt twice. Every other harness gets the lists from the core."""
    vendor = SAMPLES["claude"]("edit", repo, "vendor/ecc/x.py")
    assert not denied(run("claude", "pre", json.dumps(vendor)))
    other = agenthook.pre(Call("any-other", WRITE, (str(repo / "vendor/ecc/x.py"),), cwd=repo), repo)
    assert other.decision == "deny" and "Edit(vendor/**)" in other.message


def test_an_ask_rule_is_never_a_silent_allow(repo: Path) -> None:
    v = agenthook.pre(Call("any-other", BASH, command="uv run pytest && git push origin x", cwd=repo), repo)
    assert v.decision == "ask" and "git push" in v.message


def test_cursor_keeps_the_claude_gate_until_it_has_its_own(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The Cursor CLI runs `.claude/settings.json` hooks too. Until a Cursor
    adapter gates before the action, that imported hook is Cursor's only
    pre-edit gate, and must still refuse."""
    monkeypatch.setenv("CURSOR_VERSION", "3.0")
    assert denied(run("claude", "pre", json.dumps(SAMPLES["claude"]("edit", repo, ".env"))))


def test_a_harness_that_gates_itself_is_not_answered_for_twice(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Once Cursor has its own adapter, the imported Claude hook steps aside."""
    from types import SimpleNamespace

    monkeypatch.setenv("CURSOR_VERSION", "3.0")
    monkeypatch.setattr(harness_adapters, "_spec", lambda key: SimpleNamespace(adapter=object()))
    assert run("claude", "pre", json.dumps(SAMPLES["claude"]("edit", repo, ".env"))) == ("", "", 0)


def test_a_patch_names_every_file() -> None:
    patch = (
        "*** Begin Patch\n*** Update File: a.py\n@@\n-x\n+y\n*** Add File: .env\n+K=v\n"
        "*** Update File: b.py\n*** Move to: c.py\n*** End Patch\n"
    )
    assert patch_paths(patch) == ("a.py", ".env", "b.py", "c.py")


def test_one_bad_file_blocks_the_whole_call(repo: Path) -> None:
    c = Call("any-other", EDIT, (str(repo / "platform/ok.py"), str(repo / ".env")), cwd=repo)
    assert agenthook.pre(c, repo).decision == "deny"


# ------------------------------------------------------------- permissions --
@pytest.mark.parametrize(
    "pattern,path,hit",
    [
        ("./.env", "/r/.env", True),
        ("./.env.*", "/r/.env.local", True),
        ("**/secrets.toml", "/r/groups/a/.dlt/secrets.toml", True),
        ("**/credentials/**", "/r/x/credentials/key.json", True),
        ("vendor/**", "/r/vendor/ecc/a/b.py", True),
        ("vendor/**", "/r/platform/vendor.py", False),
        ("../*/src/**", "/r/groups/acme/projects/acme-us/src/x.py", True),
    ],
)
def test_paths_resolve_the_way_claude_resolves_them(pattern: str, path: str, hit: bool) -> None:
    base = Path("/r/groups/acme/projects/acme-eu") if pattern.startswith("../") else Path("/r")
    assert path_matches(Rule("Read", pattern, base), Path(path)) is hit


@pytest.mark.parametrize(
    "pattern,command,hit",
    [
        ("git push:*", "git push origin main", True),
        ("git push:*", "uv run pytest && git push", True),
        ("git push:*", "git pushx", False),
        ("git push:*", "echo 'git push'", False),
        ("gh pr create:*", "gh pr create --fill", True),
    ],
)
def test_bash_rules_match_a_prefix_per_segment(pattern: str, command: str, hit: bool) -> None:
    assert command_matches(Rule("Bash", pattern, Path("/r")), command) is hit


def test_a_project_session_gets_the_projects_denies(repo: Path) -> None:
    """acme-eu may not read a sister's source — a rule only its own settings carry."""
    cwd = repo / "groups" / "acme" / "projects" / "acme-eu"
    sister = repo / "groups" / "acme" / "projects" / "acme-us" / "src" / "x.py"
    v = agenthook.permission(Call("any-other", READ, (str(sister),), cwd=cwd), repo)
    assert v.decision == "deny"
    v = agenthook.permission(Call("any-other", READ, (str(sister),), cwd=repo), repo)
    assert v.decision == "allow", "at the root, the project rule does not apply"


# ---------------------------------------------------------- never closed --
@pytest.mark.parametrize("harness", [*sorted(SAMPLES), "nonesuch"])
@pytest.mark.parametrize("raw", ["", "not json", "[]", '{"tool_name": 7}'])
def test_garbage_in_is_allowed_out(harness: str, raw: str) -> None:
    for ev in ("pre", "post", "stop", "bogus"):
        _out, _err, code = run(harness, ev, raw)
        assert code == 0, f"{harness}/{ev} failed closed on {raw!r}"


@pytest.mark.parametrize(
    "command,bypasses",
    [
        # a message that mentions the flag is a message
        ('git commit -m "note: never use --no-verify here"', False),
        ('git commit -m "document core.hooksPath" -F notes.txt', False),
        ("git commit -mn", False),  # -m's value is "n"
        ("git push -n origin main", False),  # -n is dry-run for push
        ("git status --no-verify", False),
        ("echo hello", False),
        ('git commit -m "unterminated', False),
        ("", False),
        # flags of a *later* command are not git's (CodeRabbit, #584)
        ("git commit -m x && ls -ln", False),
        ("git commit -m x && git push -n", False),
        ("git commit -m x | tee log -n", False),
        # --no-verify, however it is spelled or placed
        ("git commit --no-verify -m x", True),
        ("git commit -am x -n", True),
        ("git commit -an -m x", True),
        ("git commit -n", True),
        ("git commit --no-verify --verify -m x", False),  # the last one wins
        ("git push --no-verify", True),
        ("uv run pytest && git push --no-verify origin main", True),
        # git's global options before the subcommand (CodeRabbit, #584)
        ("git -C . commit --no-verify -m x", True),
        ("git --git-dir .git --work-tree . commit -n", True),
        ("/usr/bin/git -P commit --no-verify", True),
        # pointing the hooks away
        ("git -c core.hooksPath=/dev/null commit -m x", True),
        ("git -c CORE.HOOKSPATH=/tmp push", True),
        ("git --config-env=core.hooksPath=HOOKS commit -m x", True),
        ("GIT_CONFIG_PARAMETERS=\"'core.hooksPath=/x'\" git commit -m x", True),
        ("env GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=core.hooksPath GIT_CONFIG_VALUE_0=/x git commit -m x", True),
        ("git config core.hooksPath /dev/null", True),
        ("git config set --local core.hooksPath .nohooks", True),
        ("git config --get core.hooksPath", False),
        ("git config --unset core.hooksPath", False),
        ("git -c user.name=x commit -m y", False),
        # hidden in another command
        ('sh -c "git commit --no-verify -m x"', True),
        ("bash -lc 'git -C . commit -n'", True),
        ("echo $(git commit -n -m x)", True),
        ("echo `git commit -n -m x`", True),
        ("sudo git commit --no-verify", True),
        ("timeout 30 git push --no-verify", True),
    ],
)
def test_the_no_verify_guard_is_flag_position_aware(command: str, bypasses: bool) -> None:
    assert bypasses_hooks(command) is bypasses


def test_the_neutral_vocabulary_is_closed() -> None:
    """Every mapped tool is one the core knows; a typo here is an ungated tool."""
    known = {EDIT, WRITE, BASH, READ}
    for h, table in harness_adapters.TOOLS.items():
        assert set(table.values()) <= known, h
