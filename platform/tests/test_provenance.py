"""Tests for the agent action provenance chain.

The chain is evidence, and evidence is only worth what its failure modes are
worth catching. So these tests are mostly attacks: edit a record, re-seal it,
truncate the file, reorder the stages, claim a denial that ran anyway. Each one
must be *detected*, and the test names say which attack they are.

The canonicalisation tests matter as much as the tamper ones. A digest that
depends on key order or on float formatting is a digest a second implementation
cannot reproduce, which quietly turns "verifiable by anyone" into "verifiable by
us" — and nothing fails when it does.
"""

from __future__ import annotations

import itertools
import json
import subprocess
import sys
from pathlib import Path

import pytest
from pf.provenance import (
    Revoked,
    action,
    approve,
    decision,
    execution,
    head,
    intent,
    is_revoked,
    read_all,
    report,
    revoke,
    verify_chain,
)
from pf.provenance.record import GENESIS, NonCanonical, Record, canonical_bytes, digest

VERIFIER = Path(__file__).resolve().parents[1] / "scripts" / "verify_provenance.py"


@pytest.fixture()
def root(tmp_path: Path) -> Path:
    return tmp_path


def _chain(root: Path) -> Path:
    return root / "provenance" / "chain.jsonl"


def _lines(root: Path) -> list[dict]:
    return [json.loads(x) for x in _chain(root).read_text().splitlines() if x.strip()]


def _rewrite(root: Path, lines: list[dict]) -> None:
    _chain(root).write_text(
        "\n".join(json.dumps(x, sort_keys=True, separators=(",", ":"))
                  for x in lines) + "\n")


# ---------------------------------------------------------------- canonical --

def test_key_order_does_not_change_the_digest():
    """Two dicts with the same content must hash identically."""
    a = {"b": 1, "a": {"z": True, "y": [1, 2]}}
    b = {"a": {"y": [1, 2], "z": True}, "b": 1}
    assert digest(a) == digest(b)


def test_non_ascii_is_stable():
    assert canonical_bytes({"p": "café"}) == b'{"p":"caf\xc3\xa9"}'


def test_floats_are_refused():
    """0.1 does not round-trip identically in every language; refuse it early."""
    with pytest.raises(NonCanonical):
        canonical_bytes({"cost": 0.1})


def test_hash_excludes_itself():
    rec = Record(seq=0, action_id="a", stage="intent", ts="2026-01-01T00:00:00Z",
                 actor="x", session="", group="", project="", tool="Write",
                 target="f.sql").sealed()
    assert rec.hash == digest(rec.unhashed())
    assert rec.verify_self()


# ------------------------------------------------------------------- stages --

def test_action_writes_three_stages_in_order(root: Path):
    with action(root, tool="Write", target="a.sql", summary="s"):
        pass
    recs = read_all(root)
    assert [r.stage for r in recs] == ["intent", "decision", "execution"]
    assert len({r.action_id for r in recs}) == 1
    assert recs[0].prev == GENESIS


def test_execution_is_written_even_when_the_body_raises(root: Path):
    """The failure case is the one an audit needs most."""
    with pytest.raises(ValueError), action(root, tool="Bash", target="x", summary="s"):
        raise ValueError("boom")
    recs = read_all(root)
    assert recs[-1].stage == "execution"
    assert recs[-1].payload["status"] == "error"
    assert "boom" in recs[-1].payload["detail"]


def test_chain_links_across_separate_actions(root: Path):
    with action(root, tool="Write", target="a", summary="1"):
        pass
    with action(root, tool="Write", target="b", summary="2"):
        pass
    recs = read_all(root)
    assert len(recs) == 6
    for prev, cur in itertools.pairwise(recs):
        assert cur.prev == prev.hash
    assert verify_chain(root)[0]


# ------------------------------------------------------------------ attacks --

def test_edited_record_is_detected(root: Path):
    """The cover-up: flip a recorded deny into an allow."""
    aid = intent(root, tool="Write", target="secrets.toml", summary="s").action_id
    decision(root, aid, verdict="deny", rule="denylist", message="no")
    execution(root, aid, status="blocked")

    lines = _lines(root)
    lines[1]["payload"]["verdict"] = "allow"
    _rewrite(root, lines)

    ok, breaks = verify_chain(root)
    assert not ok
    assert any(b.kind == "hash" for b in breaks)


def test_resealed_record_breaks_the_next_link(root: Path):
    """The competent cover-up: edit *and* recompute the hash.

    This is what the chain is for. Re-sealing the record fixes its own digest
    and breaks its successor's `prev`, so hiding one edit means rewriting every
    record after it — which moves the head, which is what the anchor covers.
    """
    aid = intent(root, tool="Write", target="secrets.toml", summary="s").action_id
    decision(root, aid, verdict="deny", rule="denylist", message="no")
    execution(root, aid, status="blocked")

    lines = _lines(root)
    assert lines[1]["payload"]["verdict"] == "deny"
    lines[1]["payload"]["verdict"] = "allow"          # a real change, not a no-op
    body = {k: v for k, v in lines[1].items() if k != "hash"}
    lines[1]["hash"] = digest(body)                   # …and re-seal it
    _rewrite(root, lines)

    ok, breaks = verify_chain(root)
    assert not ok
    # The forged record now hashes correctly to its own content; what gives it
    # away is record 2, whose `prev` still points at the original digest.
    assert any(b.kind == "link" and b.seq == 2 for b in breaks)


def test_removed_record_is_detected(root: Path):
    with action(root, tool="Write", target="a", summary="1"):
        pass
    lines = _lines(root)
    del lines[1]                      # drop the DECISION entirely
    _rewrite(root, lines)

    ok, breaks = verify_chain(root)
    assert not ok
    assert {b.kind for b in breaks} & {"sequence", "link"}


def test_truncation_alone_is_not_flagged_as_corruption(root: Path):
    """Cutting the tail leaves a valid prefix — which is why anchors exist.

    Pinned deliberately: the chain cannot detect its own truncation, and a test
    asserting otherwise would be encoding a guarantee this design does not make.
    An auditor holding an earlier anchored head is what catches it.
    """
    with action(root, tool="Write", target="a", summary="1"):
        pass
    lines = _lines(root)
    _rewrite(root, lines[:2])
    assert verify_chain(root)[0] is True


# ------------------------------------------------------------------- audit --

def test_ungated_execution_is_a_failure(root: Path):
    """An EXECUTION with no DECISION is work that bypassed the gate."""
    aid = intent(root, tool="Bash", target="rm -rf /", summary="s").action_id
    execution(root, aid, status="ok")
    rep = report(root)
    assert not rep.ok
    assert any(f.code == "action.ungated" for f in rep.findings)


def test_denial_that_executed_is_a_failure(root: Path):
    """A verdict the system did not impose is worse than no verdict."""
    aid = intent(root, tool="Write", target="a", summary="s").action_id
    decision(root, aid, verdict="deny", rule="denylist", message="no")
    execution(root, aid, status="ok")
    rep = report(root)
    assert not rep.ok
    assert any(f.code == "decision.not_enforced" for f in rep.findings)


def test_dangling_action_is_reported(root: Path):
    aid = intent(root, tool="Write", target="a", summary="s").action_id
    decision(root, aid, verdict="allow", rule="default")
    rep = report(root)
    assert any(f.code == "action.dangling" for f in rep.findings)


def test_self_approval_is_a_failure(root: Path, monkeypatch):
    monkeypatch.setenv("PF_ACTOR", "alice")
    aid = intent(root, tool="Write", target="a", summary="s").action_id
    decision(root, aid, verdict="hold", rule="human_oversight")
    execution(root, aid, status="blocked")
    approve(root, aid)                       # same identity approves its own work
    rep = report(root)
    assert any(f.code == "oversight.self_approved" for f in rep.findings)


def test_clean_ledger_passes(root: Path):
    with action(root, tool="Write", target="a", summary="1"):
        pass
    rep = report(root)
    assert rep.ok
    assert any(f.code == "chain.intact" for f in rep.findings)


# -------------------------------------------------------------- revocation --

def test_revoked_actor_cannot_open_an_action(root: Path):
    revoke(root, actor="*", reason="incident 42")
    stopped, why = is_revoked(root)
    assert stopped and "incident 42" in why
    with pytest.raises(Revoked):
        intent(root, tool="Write", target="a", summary="s")


def test_unreadable_revocation_file_fails_closed(root: Path):
    """'I cannot tell whether you are revoked' must not resolve to 'carry on'."""
    d = root / "provenance"
    d.mkdir(parents=True, exist_ok=True)
    (d / "revoked.json").write_text("{ not json")
    assert is_revoked(root)[0] is True


# ------------------------------------------------------- external verifier --

def test_standalone_verifier_agrees(root: Path):
    """The bundled verifier must reach our verdict without importing pf."""
    with action(root, tool="Write", target="a", summary="1"):
        pass
    proc = subprocess.run(
        [sys.executable, str(VERIFIER), str(root / "provenance")],
        capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "INTEGRITY: OK" in proc.stdout

    lines = _lines(root)
    lines[0]["actor"] = "somebody-else"
    _rewrite(root, lines)
    proc = subprocess.run(
        [sys.executable, str(VERIFIER), str(root / "provenance")],
        capture_output=True, text=True)
    assert proc.returncode == 1
    assert "INTEGRITY: FAILED" in proc.stdout


# ------------------------------------------------------------------ anchors --

def test_timestamp_request_is_well_formed_der():
    """Pinned by hand: a malformed request is rejected by the TSA, not by us."""
    from pf.provenance.anchor import build_request

    req = build_request("ab" * 32)
    assert req[0] == 0x30                        # SEQUENCE
    assert bytes.fromhex("ab" * 32) in req       # the digest is carried verbatim
    assert bytes([0x06, 0x09, 0x60, 0x86, 0x48, 0x01,
                  0x65, 0x03, 0x04, 0x02, 0x01]) in req   # sha256 OID
    assert req.endswith(bytes([0x01, 0x01, 0xFF]))         # certReq TRUE


def test_timestamp_request_rejects_a_short_digest():
    from pf.provenance.anchor import build_request

    with pytest.raises(ValueError):
        build_request("abcd")


def test_head_tracks_appends(root: Path):
    assert head(root).seq == -1
    with action(root, tool="Write", target="a", summary="1"):
        pass
    h = head(root)
    assert h.seq == 2
    assert h.hash == read_all(root)[-1].hash


def test_head_recovers_from_a_lost_sidecar(root: Path):
    """A deleted head file must not reset the chain to genesis."""
    with action(root, tool="Write", target="a", summary="1"):
        pass
    (root / "provenance" / "head.json").unlink()
    assert head(root).seq == 2
    with action(root, tool="Write", target="b", summary="2"):
        pass
    assert verify_chain(root)[0]
