"""Workflow runs written inside the repo. Every failure here is silent or
destructive: a session is left unlinked and its runs go to ~/.claude unnoticed,
a run the harness wrote is never found, or a session folder is emptied before
what it held was proven to be in the repo. Everything runs against a fake Claude
home under tmp_path; the real ~/.claude is never opened."""

from __future__ import annotations

import hashlib
import io
import json
import os
import shutil
import time
from pathlib import Path

import pytest
from conftest import REPO_ROOT
from pf import workflows
from pf.workflows import (
    Agent,
    Run,
    claude_home,
    discover,
    finalize,
    link,
    mirror,
    sessions,
    slug,
    sync,
    verify,
    watch,
)

SESSION_A = "a2f4111f-9742-41c3-9ed6-b6a1d0fc8303"
SESSION_B = "d952e142-84e3-4315-b8bd-2419b87e20eb"
DONE, RUNNING, FAILED = "done", "running", "failed"


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    """A repo root repo_root() would accept, with an underscore in the path so
    the slug rule is exercised the way the real checkout exercises it."""
    root = tmp_path / "data_platform" / "data-platform"
    (root / "platform").mkdir(parents=True)
    (root / "groups").mkdir()
    return root


@pytest.fixture()
def home(tmp_path: Path, repo: Path) -> Path:
    """A fake ~/.claude holding this repo's slug (with its `memory` dir and a
    stray session transcript file) and another repo's slug that must be ignored."""
    h = tmp_path / "claude"
    mine = h / "projects" / slug(repo)
    (mine / "memory").mkdir(parents=True)
    (mine / f"{SESSION_A}.jsonl").write_text("{}\n")
    other = (
        h / "projects" / "-Users-someone-other-repo" / "11111111-1111" / "subagents" / "workflows" / "wf_other000-000"
    )
    other.mkdir(parents=True)
    (other / "journal.jsonl").write_text('{"type":"launched"}\n')
    return h


def age(d: Path, seconds: float) -> None:
    t = time.time() - seconds
    for p in d.rglob("*"):
        os.utime(p, (t, t))
    os.utime(d, (t, t))


def write_run(
    home: Path,
    repo: Path,
    session: str,
    run_id: str,
    name: str,
    agents: list[tuple[str, str, str, str]],
    *,
    quiet: float = 1000.0,
    script: bool = True,
) -> Path:
    """agents: (agent_id, label, phase, state). Journal order is start order;
    result and failed records follow, as the harness writes them."""
    d = home / "projects" / slug(repo) / session / "subagents" / "workflows" / run_id
    d.mkdir(parents=True)
    lines: list[dict] = [{"type": "launched"}]
    for aid, label, phase, _ in agents:
        lines.append({"type": "started", "key": f"v2:{aid}", "agentId": aid, "label": label, "phase": phase})
        (d / f"agent-{aid}.meta.json").write_text(
            json.dumps({"agentType": "workflow-subagent", "description": label, "workflowPhase": phase})
        )
        (d / f"agent-{aid}.jsonl").write_text(f'{{"type":"user","agent":"{aid}"}}\n' * 4)
    for aid, _, _, state in agents:
        if state == DONE:
            lines.append({"type": "result", "key": f"v2:{aid}", "agentId": aid, "result": {"summary": "ok"}})
        elif state == FAILED:
            lines.append({"type": "failed", "key": f"v2:{aid}", "agentId": aid})
    (d / "journal.jsonl").write_text("".join(json.dumps(rec) + "\n" for rec in lines))
    if script:
        scripts = home / "projects" / slug(repo) / session / "workflows" / "scripts"
        scripts.mkdir(parents=True, exist_ok=True)
        (scripts / f"{name}-{run_id}.js").write_text(f"export const meta = {{\n  name: '{name}',\n  phases: [],\n}};\n")
    age(d, quiet)
    return d


def one(root: Path, home: Path, run_id: str) -> Run:
    return {r.run_id: r for r in discover(root, home)}[run_id]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


# --- layout ------------------------------------------------------------------


def test_slug_replaces_every_non_alphanumeric_including_underscore() -> None:
    assert (
        slug(Path("/Users/s/Documents/data_platform/data-platform")) == "-Users-s-Documents-data-platform-data-platform"
    )


def test_claude_home_honours_config_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("CLAUDE_CONFIG_DIR", raising=False)
    assert claude_home() == Path.home() / ".claude"
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / "cc"))
    assert claude_home() == tmp_path / "cc"
    # A `~` the shell never expanded would name a directory in the cwd, where
    # there are no sessions and every link would be built in the wrong place.
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", "~/elsewhere/.claude")
    assert claude_home() == Path.home() / "elsewhere" / ".claude"


def test_sessions_skips_memory_and_files(repo: Path, home: Path) -> None:
    mine = home / "projects" / slug(repo)
    (mine / SESSION_A).mkdir()
    (mine / SESSION_B).mkdir()
    assert [p.name for p in sessions(repo, home)] == [SESSION_A, SESSION_B]
    assert sessions(repo / "elsewhere", home) == []


# --- discovery ---------------------------------------------------------------


def test_discover_spans_sessions_ignores_other_slugs_and_merges_mirrors(repo: Path, home: Path) -> None:
    write_run(home, repo, SESSION_A, "wf_aaaaaaaa-001", "verify-stack", [("a1", "verify:1", "Verify", DONE)])
    write_run(
        home, repo, SESSION_B, "wf_bbbbbbbb-002", "impl-runs", [("b1", "impl:workflows", "Implement", RUNNING)], quiet=0
    )
    only = repo / "logs" / "workflows" / "wf_cccccccc-003"
    only.mkdir(parents=True)
    (only / "journal.jsonl").write_text(
        '{"type":"launched"}\n'
        '{"type":"started","agentId":"c1","label":"fix:x","phase":"Fix"}\n'
        '{"type":"result","agentId":"c1","result":{}}\n'
    )
    (only / "script.js").write_text("export const meta = {\n  name: 'moved-by-hand',\n};\n")
    (only / "README.md").write_text("# Workflow run wf_cccccccc-003\n")
    age(only, 500)
    both = repo / "logs" / "workflows" / "wf_aaaaaaaa-001"
    both.mkdir(parents=True)
    # A directory in logs/workflows counts as a run once it has a journal; that
    # is what tells a half-copied run apart from `scripts/`.
    shutil.copy2(
        home / "projects" / slug(repo) / SESSION_A / "subagents" / "workflows" / "wf_aaaaaaaa-001" / "journal.jsonl",
        both / "journal.jsonl",
    )

    found = discover(repo, home)
    assert [r.run_id for r in found] == [  # newest change first
        "wf_bbbbbbbb-002",
        "wf_cccccccc-003",
        "wf_aaaaaaaa-001",
    ]
    b, c, a = found
    assert a.session == SESSION_A and a.name == "verify-stack"
    assert a.source is not None and a.mirror == both and a.script is not None
    assert b.session == SESSION_B and b.source is not None and b.mirror is None
    assert c.session == "" and c.source is None and c.mirror == only
    assert c.name == "moved-by-hand" and c.finished == 1


def test_agent_states_come_from_the_journal_and_phases_keep_order(repo: Path, home: Path) -> None:
    write_run(
        home,
        repo,
        SESSION_A,
        "wf_aaaaaaaa-001",
        "verify-stack",
        [
            ("u1", "read:a", "Understand", DONE),
            ("u2", "read:b", "Understand", FAILED),
            ("v1", "verify:1", "Verify", DONE),
            ("v2", "verify:2", "Verify", RUNNING),
        ],
    )
    run = one(repo, home, "wf_aaaaaaaa-001")
    assert [(a.agent_id, a.state) for a in run.agents] == [("u1", DONE), ("u2", FAILED), ("v1", DONE), ("v2", RUNNING)]
    assert (run.started, run.finished, run.failed) == (4, 3, 1)
    assert list(run.phases.items()) == [("Understand", (2, 2)), ("Verify", (2, 1))]
    assert run.live and not run.complete


def test_meta_overrides_journal_label_and_a_torn_journal_line_is_skipped(repo: Path, home: Path) -> None:
    d = write_run(home, repo, SESSION_A, "wf_aaaaaaaa-001", "verify-stack", [("v1", "journal-label", "Verify", DONE)])
    (d / "agent-v1.meta.json").write_text(
        json.dumps({"agentType": "workflow-subagent", "description": "meta-label", "workflowPhase": "Review"})
    )
    with (d / "journal.jsonl").open("a") as f:
        f.write('{"type":"started","agentId":"v2","label":"half')  # mid-write
    run = one(repo, home, "wf_aaaaaaaa-001")
    assert run.agents == [Agent("v1", "meta-label", "Review", DONE)]


# --- mirroring ---------------------------------------------------------------


def test_mirror_copies_everything_once_then_nothing(repo: Path, home: Path) -> None:
    write_run(
        home,
        repo,
        SESSION_A,
        "wf_aaaaaaaa-001",
        "verify-stack",
        [("v1", "verify:1", "Verify", DONE), ("v2", "verify:2", "Verify", DONE)],
    )
    run = one(repo, home, "wf_aaaaaaaa-001")
    lines: list[str] = []
    rep = mirror(run, repo, log=lines.append)
    assert sorted(rep.copied) == [
        "agent-v1.jsonl",
        "agent-v1.meta.json",
        "agent-v2.jsonl",
        "agent-v2.meta.json",
        "journal.jsonl",
        "script.js",
    ]
    assert rep.skipped == 0 and rep.bytes > 0
    assert lines[0].startswith("[1/6]") and lines[-1].startswith("[6/6] 100% ")
    dest = repo / "logs" / "workflows" / "wf_aaaaaaaa-001"
    assert run.mirror == dest
    readme = (dest / "README.md").read_text()
    assert "wf_aaaaaaaa-001" in readme and "verify-stack" in readme
    assert "2 started, 2 finished, 0 failed" in readme and "**/logs/" in readme
    assert str(run.source) in readme
    stamp = (dest / "README.md").stat().st_mtime_ns

    again = mirror(one(repo, home, "wf_aaaaaaaa-001"), repo)
    assert again.copied == [] and again.skipped == 6
    assert (dest / "README.md").stat().st_mtime_ns == stamp  # unchanged, not rewritten


def test_mirror_recopies_a_source_file_that_grew(repo: Path, home: Path) -> None:
    d = write_run(home, repo, SESSION_A, "wf_aaaaaaaa-001", "verify-stack", [("v1", "verify:1", "Verify", RUNNING)])
    mirror(one(repo, home, "wf_aaaaaaaa-001"), repo)
    with (d / "agent-v1.jsonl").open("a") as f:
        f.write('{"type":"assistant","text":"more"}\n')
    rep = mirror(one(repo, home, "wf_aaaaaaaa-001"), repo)
    assert rep.copied == ["agent-v1.jsonl"]
    dest = repo / "logs" / "workflows" / "wf_aaaaaaaa-001"
    assert sha(dest / "agent-v1.jsonl") == sha(d / "agent-v1.jsonl")


def test_verify_reports_a_mirror_file_that_differs_only_by_content(repo: Path, home: Path) -> None:
    write_run(home, repo, SESSION_A, "wf_aaaaaaaa-001", "verify-stack", [("v1", "verify:1", "Verify", DONE)])
    run = one(repo, home, "wf_aaaaaaaa-001")
    mirror(run, repo)
    assert verify(run) == []
    bad = run.mirror / "agent-v1.jsonl"
    original = bad.read_bytes()
    stat = bad.stat()
    bad.write_bytes(b"X" * len(original))  # same size
    os.utime(bad, ns=(stat.st_atime_ns, stat.st_mtime_ns))  # same mtime
    assert verify(run) == ["agent-v1.jsonl"]
    assert mirror(run, repo).copied == []  # size and mtime cannot see it; only the hash can


# --- finalize ----------------------------------------------------------------


def test_finalize_refuses_a_live_run(repo: Path, home: Path) -> None:
    d = write_run(
        home,
        repo,
        SESSION_A,
        "wf_aaaaaaaa-001",
        "verify-stack",
        [
            ("v1", "verify:1", "Verify", DONE),
            ("v2", "verify:2", "Verify", RUNNING),
            ("v3", "verify:3", "Verify", RUNNING),
        ],
    )
    run = one(repo, home, "wf_aaaaaaaa-001")
    mirror(run, repo)
    assert finalize(run, repo) == (False, "live: 2 of 3 agents still running")
    assert d.is_dir() and run.source == d


def test_finalize_refuses_a_run_inside_its_quiet_period(repo: Path, home: Path) -> None:
    d = write_run(
        home, repo, SESSION_A, "wf_aaaaaaaa-001", "verify-stack", [("v1", "verify:1", "Verify", DONE)], quiet=0
    )
    run = one(repo, home, "wf_aaaaaaaa-001")
    mirror(run, repo)
    ok, reason = finalize(run, repo)
    assert not ok and reason.startswith("changed 0 s ago, quiet period 120 s")
    assert d.is_dir()


def test_finalize_repairs_a_damaged_mirror_copy_then_moves(repo: Path, home: Path) -> None:
    """Same size, same mtime, different bytes: mirror() cannot see it and would
    skip the file forever. finalize() re-copies what fails the hash once, and
    the run moves with a whole mirror rather than being refused every turn."""
    d = write_run(home, repo, SESSION_A, "wf_aaaaaaaa-001", "verify-stack", [("v1", "verify:1", "Verify", DONE)])
    run = one(repo, home, "wf_aaaaaaaa-001")
    mirror(run, repo)
    src = d / "journal.jsonl"
    good = sha(src)
    dst = run.mirror / "journal.jsonl"
    dst.write_bytes(b"x" * src.stat().st_size)
    os.utime(dst, (src.stat().st_mtime, src.stat().st_mtime))
    assert verify(run) == ["journal.jsonl"]
    ok, note = finalize(run, repo)
    assert ok and note == "moved to logs/workflows/wf_aaaaaaaa-001"
    assert sha(dst) == good and not d.exists()


def test_finalize_refuses_a_mismatch_the_repair_cannot_fix(
    repo: Path, home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    d = write_run(home, repo, SESSION_A, "wf_aaaaaaaa-001", "verify-stack", [("v1", "verify:1", "Verify", DONE)])
    run = one(repo, home, "wf_aaaaaaaa-001")
    mirror(run, repo)
    (run.mirror / "journal.jsonl").write_text("truncated")
    # A repair that changes nothing stands in for a source that keeps moving
    # under the copy; the hash, not the copy, decides.
    monkeypatch.setattr(workflows.shutil, "copy2", lambda *_a, **_k: None)
    assert finalize(run, repo) == (False, "mirror mismatch: journal.jsonl")
    assert d.is_dir()
    assert finalize(Run("wf_none"), repo) == (False, "no session copy to remove")


def test_finalize_rereads_the_run_before_removing_it(repo: Path, home: Path) -> None:
    """The discover() snapshot said one agent, finished long ago. A run that
    resumed since then has a new started record; the snapshot alone would
    have let rmtree through."""
    d = write_run(home, repo, SESSION_A, "wf_aaaaaaaa-001", "verify-stack", [("v1", "verify:1", "Verify", DONE)])
    run = one(repo, home, "wf_aaaaaaaa-001")
    mirror(run, repo)
    assert run.started == run.finished == 1
    with (d / "journal.jsonl").open("a") as f:
        f.write(
            json.dumps({"type": "started", "key": "v2:v9", "agentId": "v9", "label": "verify:9", "phase": "Verify"})
            + "\n"
        )
    age(d, 1000)  # quiet by mtime, so only the re-read can catch it
    assert finalize(run, repo) == (False, "live: 1 of 2 agents still running")
    assert d.is_dir()


def test_finalize_moves_a_complete_quiet_run_and_keeps_the_script(repo: Path, home: Path) -> None:
    d = write_run(
        home,
        repo,
        SESSION_A,
        "wf_aaaaaaaa-001",
        "verify-stack",
        [("v1", "verify:1", "Verify", DONE), ("v2", "verify:2", "Verify", FAILED)],
    )
    run = one(repo, home, "wf_aaaaaaaa-001")
    hashes = {p.name: sha(p) for p in d.iterdir()}
    hashes["script.js"] = sha(run.script)
    mirror(run, repo)
    logged: list[str] = []
    ok, note = finalize(run, repo, log=logged.append)
    assert ok and note == "moved to logs/workflows/wf_aaaaaaaa-001"
    assert logged == ["wf_aaaaaaaa-001 moved to logs/workflows/wf_aaaaaaaa-001"]
    assert not d.exists() and run.source is None
    dest = repo / "logs" / "workflows" / "wf_aaaaaaaa-001"
    assert {p.name: sha(p) for p in dest.iterdir() if p.name != "README.md"} == hashes
    scripts = home / "projects" / slug(repo) / SESSION_A / "workflows" / "scripts"
    assert (scripts / "verify-stack-wf_aaaaaaaa-001.js").is_file()
    after = one(repo, home, "wf_aaaaaaaa-001")
    assert after.source is None and after.mirror == dest and after.name == "verify-stack"
    assert after.session == "" and after.finished == 2 and after.failed == 1


def test_a_symlinked_mirror_is_refused_and_the_session_copy_survives(repo: Path, home: Path) -> None:
    d = write_run(home, repo, SESSION_A, "wf_aaaaaaaa-001", "verify-stack", [("v1", "verify:1", "Verify", DONE)])
    link = repo / "logs" / "workflows" / "wf_aaaaaaaa-001"
    link.parent.mkdir(parents=True)
    link.symlink_to(d)
    before = sorted(p.name for p in d.iterdir())

    run = one(repo, home, "wf_aaaaaaaa-001")
    assert run.mirror is None  # a link to the session copy is not a mirror of it
    rep = mirror(run, repo)
    assert rep.copied == [] and rep.skipped == 0 and rep.refused == "mirror path is a symlink"
    assert sorted(p.name for p in d.iterdir()) == before  # no README or script through the link
    assert finalize(run, repo) == (False, "mirror path is a symlink")
    assert d.is_dir() and run.source == d

    results = sync(repo, home, move=True)
    assert [(r.copied, r.moved, r.refused) for r in results] == [(0, False, "mirror path is a symlink")]
    assert d.is_dir() and (d / "journal.jsonl").is_file() and link.is_symlink()


def test_a_linked_mirror_root_is_refused_by_resolved_path(repo: Path, home: Path) -> None:
    d = write_run(home, repo, SESSION_A, "wf_aaaaaaaa-001", "verify-stack", [("v1", "verify:1", "Verify", DONE)])
    (repo / "logs").mkdir()
    (repo / "logs" / "workflows").symlink_to(d.parent)
    entry = repo / "logs" / "workflows" / "wf_aaaaaaaa-001"
    assert entry.is_dir() and not entry.is_symlink()  # an is_symlink check alone would miss it

    run = one(repo, home, "wf_aaaaaaaa-001")
    assert run.mirror is None
    assert mirror(run, repo).refused == "mirror path resolves into the session folder"
    assert finalize(run, repo) == (False, "mirror path resolves into the session folder")
    assert d.is_dir() and sorted(p.name for p in d.iterdir()) == [
        "agent-v1.jsonl",
        "agent-v1.meta.json",
        "journal.jsonl",
    ]


# --- sync and watch ----------------------------------------------------------


def test_sync_with_move_reports_each_run(repo: Path, home: Path) -> None:
    write_run(home, repo, SESSION_A, "wf_aaaaaaaa-001", "verify-stack", [("v1", "verify:1", "Verify", DONE)])
    write_run(
        home, repo, SESSION_B, "wf_bbbbbbbb-002", "impl-runs", [("b1", "impl:workflows", "Implement", RUNNING)], quiet=0
    )
    first = {r.run_id: r for r in sync(repo, home)}
    assert first["wf_aaaaaaaa-001"].copied == 4 and not first["wf_aaaaaaaa-001"].moved
    assert first["wf_bbbbbbbb-002"].copied == 4 and first["wf_bbbbbbbb-002"].note == ""

    second = {r.run_id: r for r in sync(repo, home, move=True)}
    assert second["wf_aaaaaaaa-001"].copied == 0 and second["wf_aaaaaaaa-001"].moved
    assert second["wf_aaaaaaaa-001"].note == "moved to logs/workflows/wf_aaaaaaaa-001"
    assert not second["wf_bbbbbbbb-002"].moved
    assert second["wf_bbbbbbbb-002"].note == "live: 1 of 1 agents still running"
    assert (repo / "logs" / "workflows" / "wf_aaaaaaaa-001" / "journal.jsonl").is_file()
    assert not (home / "projects" / slug(repo) / SESSION_A / "subagents" / "workflows" / "wf_aaaaaaaa-001").exists()
    assert [r.run_id for r in sync(repo, home, move=True)] == ["wf_bbbbbbbb-002"]


def test_watch_prints_only_on_change(repo: Path, home: Path) -> None:
    d = write_run(
        home,
        repo,
        SESSION_A,
        "wf_aaaaaaaa-001",
        "verify-stack",
        [("v1", "verify:1", "Verify", DONE), ("v2", "verify:2", "Verify", RUNNING)],
    )
    lines: list[str] = []
    per_round: list[int] = []

    def until() -> bool:
        per_round.append(len(lines))
        if len(per_round) == 2:  # lands between round 2 and round 3
            with (d / "journal.jsonl").open("a") as f:
                f.write(json.dumps({"type": "result", "agentId": "v2", "result": {}}) + "\n")
        return False

    watch(repo, home, interval=0, log=lines.append, until=until, max_rounds=3)
    assert per_round == [2, 2, 4]
    assert lines[0].startswith("wf_aaaaaaaa-001 verify-stack · Verify 1/2 done · ")
    assert lines[0].endswith(" B · verify:2")
    assert lines[1] == "  ▸ [Verify] verify:2"
    assert lines[2].startswith("wf_aaaaaaaa-001 verify-stack · Verify 2/2 done · ")
    assert lines[3] == "  ✓ [Verify] verify:2"
    dest = repo / "logs" / "workflows" / "wf_aaaaaaaa-001"
    assert sha(dest / "journal.jsonl") == sha(d / "journal.jsonl")  # mirrored as it went


def test_watch_announces_a_new_agent_and_a_failure(repo: Path, home: Path) -> None:
    d = write_run(home, repo, SESSION_A, "wf_aaaaaaaa-001", "verify-stack", [("v1", "verify:1", "Verify", DONE)])
    lines: list[str] = []
    rounds = [0]

    def until() -> bool:
        rounds[0] += 1
        with (d / "journal.jsonl").open("a") as f:
            if rounds[0] == 1:
                f.write('{"type":"started","agentId":"r1","label":"review:a","phase":"Review"}\n')
            elif rounds[0] == 2:
                f.write('{"type":"failed","agentId":"r1"}\n')
        return False

    watch(repo, home, interval=0, log=lines.append, until=until, max_rounds=3)
    assert lines[0].startswith("wf_aaaaaaaa-001 verify-stack · Verify 1/1 done · ")
    assert lines[1].startswith("wf_aaaaaaaa-001 verify-stack · Review 0/1 done · ")
    assert lines[2] == "  ▸ [Review] review:a"
    assert lines[3].startswith("wf_aaaaaaaa-001 verify-stack · Review 1/1 done (1 failed) · ")
    assert lines[4] == "  ✗ [Review] review:a"
    assert len(lines) == 5


def test_progress_line_format() -> None:
    agents = [Agent("i1", "impl:loops", "Implement", DONE)]
    agents += [Agent(f"v{i}", f"verify:{i}", "Verify", DONE) for i in range(11)]
    agents += [Agent("v11", "verify:11", "Verify", FAILED)]
    agents += [Agent(f"v{i}", f"verify:{i}", "Verify", RUNNING) for i in range(12, 47)]
    agents += [Agent("v47", "verify:2:Cached-prefix-tokens-hold", "Verify", RUNNING)]
    run = Run("wf_7a1bfaf8-4d1", name="commodity-engineering", agents=agents, bytes=16_900_000)
    assert run.progress_line() == (
        "wf_7a1bfaf8-4d1 commodity-engineering · Verify 12/48 done (1 failed) · 16.9 MB · verify:2:Cached-prefix…"
    )
    assert Run("wf_x").progress_line() == "wf_x · launched, no agents yet · 0 B"


# --- a run that vanishes under a reader ---------------------------------------


def test_a_source_moved_away_mid_flight_breaks_nothing(repo: Path, home: Path) -> None:
    """The Stop hook moves finished runs while a `watch` in another terminal
    is still scanning them. Every reader must shrug at a path that was there
    a moment ago."""
    d = write_run(home, repo, SESSION_A, "wf_aaaaaaaa-001", "verify-stack", [("v1", "verify:1", "Verify", DONE)])
    run = one(repo, home, "wf_aaaaaaaa-001")
    mirror(run, repo)
    shutil.rmtree(d)
    assert mirror(run, repo).copied == []
    assert finalize(run, repo) == (False, "session copy already gone")
    assert (repo / "logs" / "workflows" / "wf_aaaaaaaa-001" / "journal.jsonl").is_file()
    assert one(repo, home, "wf_aaaaaaaa-001").source is None


def test_watch_survives_a_run_removed_between_rounds(repo: Path, home: Path) -> None:
    d = write_run(home, repo, SESSION_A, "wf_aaaaaaaa-001", "verify-stack", [("v1", "verify:1", "Verify", DONE)])
    lines: list[str] = []
    rounds = {"n": 0}

    def until() -> bool:
        rounds["n"] += 1
        if rounds["n"] == 1:
            shutil.rmtree(d)  # moved by a hook while the watcher sleeps
        return rounds["n"] >= 3

    watch(repo, home, interval=0, log=lines.append, until=until)
    assert lines and lines[0].startswith("wf_aaaaaaaa-001 verify-stack")
    assert not any("Traceback" in ln for ln in lines)


def test_watch_is_quiet_while_a_transcript_merely_grows(repo: Path, home: Path) -> None:
    """Every round a live transcript is a few kilobytes longer. That is not
    news; a line per round is a ticker nobody reads. Size is reported only
    when it crosses a step."""
    d = write_run(home, repo, SESSION_A, "wf_aaaaaaaa-001", "verify-stack", [("v1", "verify:1", "Verify", RUNNING)])
    lines: list[str] = []
    per_round: list[int] = []
    transcript = d / "agent-v1.jsonl"

    def until() -> bool:
        per_round.append(len(lines))
        with transcript.open("a") as f:
            f.write("x" * (1_000 if len(per_round) == 1 else workflows.SIZE_STEP))
        return False

    watch(repo, home, interval=0, log=lines.append, until=until, max_rounds=3)
    assert per_round == [2, 2, 3]  # first sight; +1 kB is silent; +one step prints
    assert lines[2].startswith("wf_aaaaaaaa-001 verify-stack · Verify 0/1 done · ")


# --- linking a session into the repo -----------------------------------------
# The link is the whole strategy: the harness writes a run inside the repo
# because the two directories it writes to are symlinks pointing there. Nothing
# is copied afterwards, so what these tests protect is the link itself, and the
# refusals that keep it from destroying a run it cannot move.


def session_folder(home: Path, repo: Path, session: str) -> Path:
    d = home / "projects" / slug(repo) / session
    d.mkdir(parents=True, exist_ok=True)
    return d


def test_link_points_both_session_directories_at_the_repo(repo: Path, home: Path) -> None:
    sess = session_folder(home, repo, SESSION_A)

    reports = link(repo, home)

    assert [(r.kind, r.state) for r in reports] == [("runs", "created"), ("scripts", "created")]
    runs, scripts = sess / "subagents" / "workflows", sess / "workflows" / "scripts"
    assert runs.is_symlink() and runs.resolve() == (repo / "logs" / "workflows").resolve()
    assert scripts.is_symlink() and scripts.resolve() == (repo / "logs" / "workflows" / "scripts").resolve()
    # `workflows/` itself stays a real directory on purpose: Claude Code's
    # retention sweep recurses into it with readdir, which follows a symlinked
    # directory but not a symlinked entry inside one.
    assert (sess / "workflows").is_dir() and not (sess / "workflows").is_symlink()
    # What the harness writes through either link lands in the repo, which is
    # the only claim that matters.
    (runs / "wf_new00000-001").mkdir()
    (scripts / "in-place-wf_new00000-001.js").write_text("export const meta = {};")
    assert (repo / "logs" / "workflows" / "wf_new00000-001").is_dir()
    assert (repo / "logs" / "workflows" / "scripts" / "in-place-wf_new00000-001.js").is_file()
    assert (repo / "logs" / "workflows" / "README.md").is_file()


def test_link_is_idempotent(repo: Path, home: Path) -> None:
    session_folder(home, repo, SESSION_A)
    link(repo, home)

    again = link(repo, home)

    assert {r.state for r in again} == {"linked"}
    assert all(r.ok for r in again)


def test_link_refuses_a_session_that_already_holds_runs(repo: Path, home: Path) -> None:
    d = write_run(home, repo, SESSION_A, "wf_aaaaaaaa-001", "verify-stack", [("a1", "verify:1", "Verify", DONE)])

    reports = link(repo, home)

    assert [r.state for r in reports] == ["refused", "refused"]
    assert "re-run with --adopt" in reports[0].note
    assert d.is_dir() and not d.parent.is_symlink()


def test_link_adopts_runs_and_scripts_and_leaves_the_launch_record(repo: Path, home: Path) -> None:
    d = write_run(home, repo, SESSION_A, "wf_aaaaaaaa-001", "verify-stack", [("a1", "verify:1", "Verify", DONE)])
    sess = home / "projects" / slug(repo) / SESSION_A
    record = sess / "workflows" / "wf_aaaaaaaa-001.json"
    record.write_text('{"runId":"wf_aaaaaaaa-001","script":"export const meta = {}"}')
    script = sess / "workflows" / "scripts" / "verify-stack-wf_aaaaaaaa-001.js"
    before = {p.name: sha(p) for p in sorted(d.rglob("*")) if p.is_file()}
    script_sha = sha(script)

    reports = link(repo, home, adopt=True)

    assert {r.state for r in reports} == {"adopted"}
    repo_runs = repo / "logs" / "workflows"
    moved = {
        p.name: sha(p)
        for p in sorted((repo_runs / "wf_aaaaaaaa-001").rglob("*"))
        if p.is_file() and p.name not in workflows.ADOPTION_EXTRAS
    }
    assert moved == before  # byte for byte, not merely present
    assert sha(repo_runs / "scripts" / script.name) == script_sha
    assert (sess / "subagents" / "workflows").is_symlink()
    assert (sess / "workflows" / "scripts").is_symlink()
    # The run and its script are in the repo, and the paths that used to lead
    # to them now lead there too instead of breaking.
    for old in (d, script):
        assert old.resolve().is_relative_to(repo_runs.resolve())
    assert script.is_file()  # resolve() alone would pass for a path that never existed
    # The launch record is deliberately left where it was: `workflows/` cannot
    # be linked without handing the retention sweep a way into the repo, and the
    # record only duplicates the script text that is now in scripts/.
    assert record.is_file() and not record.is_symlink()
    assert not (repo_runs / "wf_aaaaaaaa-001.json").exists()
    # and the adopted run now reads as one that was written in place
    run = one(repo, home, "wf_aaaaaaaa-001")
    assert run.in_repo and run.source is None and run.mirror == repo_runs / "wf_aaaaaaaa-001"


def test_link_refuses_to_adopt_while_an_agent_is_still_running(repo: Path, home: Path) -> None:
    d = write_run(
        home, repo, SESSION_A, "wf_aaaaaaaa-001", "impl-runs", [("a1", "impl:x", "Implement", RUNNING)], quiet=0
    )

    reports = link(repo, home, adopt=True)

    runs = next(r for r in reports if r.kind == "runs")
    assert runs.state == "refused" and "still running" in runs.note
    # the live run keeps the directory the harness is writing to, and nothing
    # was copied into the repo on the way to finding that out
    assert d.is_dir() and not d.parent.is_symlink()
    assert not (repo / "logs" / "workflows" / d.name).exists()


def test_link_creates_a_session_folder_the_harness_has_not_made_yet(repo: Path, home: Path) -> None:
    """What the SessionStart hook depends on: at that moment the folder may not
    exist, and a link made after the first run has started is already too late."""
    sess = home / "projects" / slug(repo) / "b0b0b0b0-0000-0000-0000-000000000000"
    assert not sess.exists()

    reports = link(repo, home, session_dir=sess)

    assert {r.state for r in reports} == {"created"}
    assert (sess / "subagents" / "workflows").is_symlink()
    assert (sess / "workflows" / "scripts").is_symlink()


def test_link_refuses_a_link_that_points_somewhere_else(repo: Path, home: Path) -> None:
    sess = session_folder(home, repo, SESSION_A)
    (sess / "subagents").mkdir()
    elsewhere = repo / "elsewhere"
    elsewhere.mkdir()
    (sess / "subagents" / "workflows").symlink_to(elsewhere)

    runs = next(r for r in link(repo, home, adopt=True) if r.kind == "runs")

    assert runs.state == "refused" and "already a link" in runs.note
    assert (sess / "subagents" / "workflows").resolve() == elsewhere.resolve()


def test_link_refuses_a_target_inside_the_claude_folder(repo: Path, home: Path) -> None:
    """A repo kept under ~/.claude would make the link point back into the
    folder it exists to empty."""
    inside = home / "checkout"
    (inside / "platform").mkdir(parents=True)
    (inside / "groups").mkdir()
    sess = home / "projects" / slug(inside) / SESSION_A

    reports = link(inside, home, session_dir=sess)

    assert {r.state for r in reports} == {"refused"}
    assert all("inside the Claude Code folder" in r.note for r in reports)


def test_link_dry_run_states_the_facts_and_changes_nothing(repo: Path, home: Path) -> None:
    d = write_run(home, repo, SESSION_A, "wf_aaaaaaaa-001", "verify-stack", [("a1", "verify:1", "Verify", DONE)])

    reports = link(repo, home, dry_run=True)

    assert [r.state for r in reports] == ["unlinked", "unlinked"]
    assert "1 item(s) to adopt" in reports[0].note
    assert not (repo / "logs").exists()
    assert d.is_dir() and not d.parent.is_symlink()


def test_link_narrows_a_link_the_retention_sweep_could_follow(repo: Path, home: Path) -> None:
    """An earlier version linked `workflows/` itself. Claude Code sweeps old
    sessions by recursing into that directory with readdir, which follows a
    symlinked directory, so the link handed the sweep a route into the repo and
    a licence to delete every run older than the cutoff. Re-linking has to undo
    it without touching what is already in the repo."""
    sess = session_folder(home, repo, SESSION_A)
    runs = repo / "logs" / "workflows"
    (runs / "scripts").mkdir(parents=True)
    (runs / "wf_aaaaaaaa-001.json").write_text('{"runId":"wf_aaaaaaaa-001"}')
    (runs / "scripts" / "verify-stack-wf_aaaaaaaa-001.js").write_text("export const meta = {};")
    (sess / "workflows").symlink_to(runs)

    reports = link(repo, home)

    sweep = next(r for r in reports if r.kind == "sweep")
    assert sweep.state == "narrowed" and sweep.ok
    assert (sess / "workflows").is_dir() and not (sess / "workflows").is_symlink()
    assert (sess / "workflows" / "scripts").is_symlink()
    # and nothing the link used to reach was removed with it
    assert (runs / "wf_aaaaaaaa-001.json").is_file()
    assert (runs / "scripts" / "verify-stack-wf_aaaaaaaa-001.js").is_file()


def test_a_wide_link_is_reported_before_it_is_narrowed(repo: Path, home: Path) -> None:
    sess = session_folder(home, repo, SESSION_A)
    (repo / "logs" / "workflows").mkdir(parents=True)
    (sess / "workflows").symlink_to(repo / "logs" / "workflows")

    reports = link(repo, home, dry_run=True)

    sweep = next(r for r in reports if r.kind == "sweep")
    assert sweep.state == "unlinked" and not sweep.ok
    assert "retention sweep" in sweep.note
    assert (sess / "workflows").is_symlink()  # --check changed nothing


def test_link_recreates_a_target_that_was_deleted_under_it(repo: Path, home: Path) -> None:
    """`logs/` is ignored by git, so `git clean -xdf` takes the target and
    leaves the links dangling. The harness cannot create a run directory through
    a dangling link, so the next run would fail rather than land elsewhere."""
    session_folder(home, repo, SESSION_A)
    link(repo, home)
    shutil.rmtree(repo / "logs" / "workflows")

    assert [r.state for r in link(repo, home, dry_run=True)] == ["unlinked", "unlinked"]
    assert {r.state for r in link(repo, home)} == {"linked"}
    assert (repo / "logs" / "workflows" / "scripts").is_dir()


def test_discover_survives_a_session_link_that_loops(repo: Path, home: Path) -> None:
    """Not something link() can produce, but a hand-made one must not take
    `pf workflow list` down with it."""
    linked_run(repo, home, "wf_dddddddd-004", "in-place", [("d1", "impl:x", "Implement", DONE)])
    other = session_folder(home, repo, SESSION_B)
    (other / "subagents").mkdir()
    (other / "subagents" / "workflows").symlink_to(other / "subagents" / "workflows")

    found = discover(repo, home)

    assert [r.run_id for r in found] == ["wf_dddddddd-004"]
    # and the same loop is a refusal from link(), not a traceback
    bad = next(r for r in link(repo, home) if r.session == SESSION_B and r.kind == "runs")
    assert bad.state == "refused" and "loop" in bad.note.lower()


def test_link_refuses_a_file_it_does_not_recognise(repo: Path, home: Path) -> None:
    sess = session_folder(home, repo, SESSION_A)
    (sess / "subagents" / "workflows").mkdir(parents=True)
    (sess / "subagents" / "workflows" / "notes.txt").write_text("mine")

    runs = next(r for r in link(repo, home, adopt=True) if r.kind == "runs")

    assert runs.state == "refused" and "not a workflow run" in runs.note
    assert (sess / "subagents" / "workflows" / "notes.txt").is_file()


# --- a run written in place --------------------------------------------------


def linked_run(
    repo: Path, home: Path, run_id: str, name: str, agents: list[tuple[str, str, str, str]], *, quiet: float = 1000.0
) -> Path:
    """A run as the harness writes it once the session is linked: through the
    session path, landing in the repo."""
    session_folder(home, repo, SESSION_A)
    link(repo, home)
    d = home / "projects" / slug(repo) / SESSION_A / "subagents" / "workflows" / run_id
    d.mkdir()
    lines = [{"type": "launched"}]
    for aid, label, phase, state in agents:
        lines.append({"type": "started", "agentId": aid, "label": label, "phase": phase})
        (d / f"agent-{aid}.jsonl").write_text('{"type":"user"}\n')
        if state == DONE:
            lines.append({"type": "result", "agentId": aid, "result": {}})
    (d / "journal.jsonl").write_text("".join(json.dumps(r) + "\n" for r in lines))
    scripts = repo / "logs" / "workflows" / "scripts"
    scripts.mkdir(parents=True, exist_ok=True)
    (scripts / f"{name}-{run_id}.js").write_text(f"export const meta = {{\n  name: '{name}',\n}};\n")
    age(repo / "logs" / "workflows" / run_id, quiet)
    return repo / "logs" / "workflows" / run_id


def test_a_run_written_through_the_link_is_reported_as_in_the_repo(repo: Path, home: Path) -> None:
    d = linked_run(repo, home, "wf_dddddddd-004", "in-place", [("d1", "impl:x", "Implement", DONE)])

    run = one(repo, home, "wf_dddddddd-004")

    assert run.in_repo and run.source is None and run.mirror == d
    assert run.name == "in-place" and run.finished == 1
    # Every linked session sees the same directory, so claiming one launched it
    # would be a guess.
    assert run.session == ""


def test_neither_sync_nor_finalize_touches_a_run_written_in_place(repo: Path, home: Path) -> None:
    d = linked_run(repo, home, "wf_dddddddd-004", "in-place", [("d1", "impl:x", "Implement", DONE)])
    run = one(repo, home, "wf_dddddddd-004")

    assert sync(repo, home, move=True) == []
    assert finalize(run, repo) == (False, "no session copy to remove")
    assert mirror(run, repo).copied == []
    assert (d / "journal.jsonl").is_file()


def test_the_scripts_directory_is_not_mistaken_for_a_run(repo: Path, home: Path) -> None:
    scripts = repo / "logs" / "workflows" / "scripts"
    scripts.mkdir(parents=True)
    (scripts / "in-place-wf_dddddddd-004.js").write_text("export const meta = {};")

    assert discover(repo, home) == []


# --- the SessionStart hook ---------------------------------------------------


def hook_module():
    import importlib.util

    path = (REPO_ROOT / "platform") / "hooks" / "session_start.py"
    spec = importlib.util.spec_from_file_location("session_start_hook", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_the_hook_takes_the_session_folder_from_the_transcript_path(repo: Path, home: Path) -> None:
    """Preferred over rebuilding the path, because it is the slug and home the
    harness actually chose."""
    mod = hook_module()
    transcript = home / "projects" / slug(repo) / f"{SESSION_B}.jsonl"

    got = mod.session_dir({"transcript_path": str(transcript)}, home, repo)

    assert got == home / "projects" / slug(repo) / SESSION_B


def test_the_hook_falls_back_to_the_session_id_and_gives_up_without_one(repo: Path, home: Path) -> None:
    mod = hook_module()

    assert mod.session_dir({"session_id": SESSION_B}, home, repo) == (home / "projects" / slug(repo) / SESSION_B)
    assert mod.session_dir({}, home, repo) is None


# --- what the review found ---------------------------------------------------


def test_finalize_refuses_even_when_asked_for_no_quiet_period(repo: Path, home: Path) -> None:
    """A run between two phases has a result for every agent that has started,
    so the quiet period is the only guard left between adoption and an rmtree of
    a directory the harness is still writing to. `--quiet-for 0` asks for that
    guard to be switched off; finalize floors it instead."""
    d = write_run(
        home, repo, SESSION_A, "wf_aaaaaaaa-001", "verify-stack", [("a1", "verify:1", "Verify", DONE)], quiet=0
    )
    run = {r.run_id: r for r in discover(repo, home, quiet_for=0.0)}["wf_aaaaaaaa-001"]
    assert run.complete  # complete by the caller's own reckoning
    mirror(run, repo)

    moved, note = finalize(run, repo)

    assert not moved and "quiet period 120" in note
    assert (d / "journal.jsonl").is_file()
    assert [r.moved for r in sync(repo, home, move=True, quiet_for=0.0)] == [False]


def test_a_linked_session_does_not_erase_another_session_s_copy(repo: Path, home: Path) -> None:
    """The run id is in the repo and, still live, in a session that was never
    linked. Reporting it as safely in the repo would hide a directory that is
    still growing under ~/.claude, and stop adoption ever looking at it."""
    session_folder(home, repo, SESSION_B)
    link(repo, home)
    d = write_run(
        home, repo, SESSION_A, "wf_dddddddd-004", "in-place", [("d1", "impl:x", "Implement", RUNNING)], quiet=0
    )
    mirror(one(repo, home, "wf_dddddddd-004"), repo)  # copied, not yet moved

    found = one(repo, home, "wf_dddddddd-004")

    assert found.source == d and found.mirror is not None
    assert not found.in_repo and found.live
    assert [r.moved for r in sync(repo, home, move=True)] == [False]


def test_link_refuses_a_run_entry_that_links_out_of_the_repo(repo: Path, home: Path) -> None:
    sess = session_folder(home, repo, SESSION_A)
    (sess / "subagents" / "workflows").mkdir(parents=True)
    elsewhere = repo / "elsewhere" / "wf_eeeeeeee-005"
    elsewhere.mkdir(parents=True)
    (elsewhere / "journal.jsonl").write_text('{"type":"launched"}\n')
    (sess / "subagents" / "workflows" / "wf_eeeeeeee-005").symlink_to(elsewhere)

    runs = next(r for r in link(repo, home, adopt=True) if r.kind == "runs")

    assert runs.state == "refused" and "move it by hand" in runs.note
    assert (elsewhere / "journal.jsonl").is_file()


def test_link_refuses_a_path_that_leads_outside_the_session_folder(repo: Path, home: Path) -> None:
    """A symlink above the leaf puts an unrelated directory in front of
    adoption, which would empty it into logs/."""
    sess = session_folder(home, repo, SESSION_A)
    outside = repo / "outside"
    (outside / "workflows").mkdir(parents=True)
    (outside / "workflows" / "notes.md").write_text("someone's notes")
    (sess / "subagents").symlink_to(outside)

    runs = next(r for r in link(repo, home, adopt=True) if r.kind == "runs")

    assert runs.state == "refused" and "outside the session folder" in runs.note
    assert (outside / "workflows" / "notes.md").is_file()


def test_a_run_directory_the_harness_has_not_journalled_yet_is_visible(repo: Path, home: Path) -> None:
    """Before the journal exists there is already a directory and a meta file.
    Calling that "not a run" hides it from `list` and makes adoption refuse the
    whole session for holding something it cannot name."""
    sess = session_folder(home, repo, SESSION_A)
    d = sess / "subagents" / "workflows" / "wf_ffffffff-006"
    d.mkdir(parents=True)
    (d / "agent-f1.meta.json").write_text(json.dumps({"description": "impl:x", "workflowPhase": "Implement"}))

    run = one(repo, home, "wf_ffffffff-006")

    assert run.started == 1 and run.finished == 0 and run.live
    # and the refusal names what is true about it, not that it is unrecognised
    runs = next(r for r in link(repo, home, adopt=True) if r.kind == "runs")
    assert runs.state == "refused" and "still running" in runs.note


def test_sessions_include_a_project_cwd_session(repo: Path, home: Path) -> None:
    """`pf work <group> <project>` launches with the project as cwd, so Claude
    Code files that session under the project's own slug."""
    project = repo / "groups" / "commodity" / "projects" / "commodity-india"
    project.mkdir(parents=True)
    (home / "projects" / slug(project) / SESSION_B).mkdir(parents=True)
    (home / "projects" / slug(repo) / SESSION_A).mkdir(parents=True)
    # a sibling checkout whose slug starts with this one's must not be swept in
    (home / "projects" / (slug(repo) + "-extra") / "99999999-9999").mkdir(parents=True)

    found = sessions(repo, home)

    assert [p.name for p in found] == [SESSION_A, SESSION_B]
    assert {r.session for r in link(repo, home, dry_run=True)} == {SESSION_A, SESSION_B}


def test_the_hook_states_where_this_session_writes(repo: Path, home: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Its stdout goes into the model's context at every session start, so it is
    one short line — but it is never nothing.

    Silence on success was the earlier contract and it hid the failure that
    actually happened: a link was refused, the refusal was printed once, and
    every session afterwards said nothing at all. The repository's position
    stayed "contained" while the state was "outside", and no one could tell the
    two apart without running a command they had no reason to run. SC-4 in
    docs/SESSION-CONTAINMENT.md.
    """
    mod = hook_module()
    sess = home / "projects" / slug(repo) / SESSION_B
    payload = json.dumps({"session_id": SESSION_B, "cwd": str(repo)})

    monkey = pytest.MonkeyPatch()
    monkey.setattr("sys.stdin", io.StringIO(payload))
    monkey.setattr(mod, "repo_root", lambda _start: repo)
    monkey.setenv("CLAUDE_CONFIG_DIR", str(home))
    assert mod.main() == 0
    said = capsys.readouterr().out.strip().splitlines()
    assert said, "a session that said nothing cannot be told from a broken one"
    assert said[-1].startswith("files: "), said
    assert (sess / "subagents" / "workflows").is_symlink()

    # now make one of them impossible and check the refusal is reported
    (sess / "subagents" / "workflows").unlink()
    (sess / "subagents" / "workflows").symlink_to(repo / "somewhere-else")
    monkey.setattr("sys.stdin", io.StringIO(payload))
    assert mod.main() == 0
    out = capsys.readouterr().out
    assert "already a link" in out and "OUTSIDE the repo" in out
    monkey.undo()


def test_link_refuses_a_directory_reached_through_a_symlinked_parent(repo: Path, home: Path) -> None:
    """The boundary check cannot be gated on the leaf existing: a foreign
    directory with no `workflows` child passes every other test and ends at
    symlink_to(), which writes a link into a stranger's directory and then
    reports the session as linked."""
    sess = session_folder(home, repo, SESSION_A)
    outside = repo / "someone-elses"
    outside.mkdir()
    (outside / "their-file.txt").write_text("mine")
    (sess / "subagents").symlink_to(outside)

    runs = next(r for r in link(repo, home, adopt=True) if r.kind == "runs")

    assert runs.state == "refused" and "outside the session folder" in runs.note
    assert sorted(p.name for p in outside.iterdir()) == ["their-file.txt"]


def test_a_session_directory_that_is_a_link_is_not_one_of_ours(repo: Path, home: Path) -> None:
    """`is_dir()` follows a link, so an entry pointing at an unrelated directory
    would be enumerated as this repo's session and have its contents adopted."""
    elsewhere = repo / "other-agent" / "subagents" / "workflows" / "wf_zzzzzzzz-009"
    elsewhere.mkdir(parents=True)
    (elsewhere / "journal.jsonl").write_text('{"type":"launched"}\n')
    (home / "projects" / slug(repo) / SESSION_A).symlink_to(repo / "other-agent")

    assert sessions(repo, home) == []
    assert link(repo, home, adopt=True) == []
    assert (elsewhere / "journal.jsonl").is_file()
    assert not (repo / "logs" / "workflows" / "wf_zzzzzzzz-009").exists()


def test_discover_prefers_the_session_copy_that_is_still_growing(repo: Path, home: Path) -> None:
    """Two sessions holding the same run id: one is a stale copy. Reporting the
    stale one hides a directory that is still being written."""
    write_run(home, repo, SESSION_A, "wf_dddddddd-004", "in-place", [("d1", "impl:x", "Implement", DONE)], quiet=5000)
    fresh = write_run(
        home, repo, SESSION_B, "wf_dddddddd-004", "in-place", [("d1", "impl:x", "Implement", DONE)], quiet=10
    )

    run = one(repo, home, "wf_dddddddd-004")

    assert run.source == fresh and run.session == SESSION_B
