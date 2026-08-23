"""The audit: does the ledger say what it claims, and does anyone else agree.

Four questions, in order of what they can prove:

  1. **Integrity** — does every record hash to its digest, and does every link
     match? Catches edits. Proves nothing against a full rewrite.
  2. **Completeness** — does every action have all three stages? Catches the
     more interesting failure, which is not a forged record but a missing one:
     an EXECUTION with no DECISION is work that bypassed the gate.
  3. **Coverage** — how much of the chain sits under a timestamp? Records
     written after the last anchor are trusted on our word alone.
  4. **Oversight** — were held actions approved by someone other than the
     actor who raised them?

A clean result on 1 alone is the answer that flatters us most and means least,
so `report()` never returns integrity without the other three.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from pf.provenance import anchor as anchor_mod
from pf.provenance.chain import Break, head, read_all
from pf.provenance.chain import verify as verify_chain
from pf.provenance.ledger import actions, approvals


@dataclass
class Finding:
    level: str        # ok | warn | fail
    code: str
    detail: str


@dataclass
class Report:
    records: int = 0
    actions_total: int = 0
    intact: bool = True
    breaks: list[Break] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    anchored_seq: int = -1
    head_seq: int = -1

    @property
    def unanchored(self) -> int:
        """Records written since the last successful anchor."""
        return max(0, self.head_seq - self.anchored_seq)

    @property
    def ok(self) -> bool:
        return self.intact and not [f for f in self.findings if f.level == "fail"]

    @property
    def exit_code(self) -> int:
        if not self.ok:
            return 1
        return 0


def report(root: Path, *, check_anchors: bool = False) -> Report:
    """Full audit. `check_anchors` shells out to openssl/ots and needs network."""
    rep = Report()

    # 1. integrity
    intact, breaks = verify_chain(root)
    rep.intact, rep.breaks = intact, breaks
    records = read_all(root)
    rep.records = len(records)
    rep.head_seq = head(root).seq
    if intact:
        rep.findings.append(Finding("ok", "chain.intact",
                                    f"{len(records)} records hash-linked from genesis"))
    else:
        rep.findings.append(Finding("fail", "chain.broken",
                                    f"{len(breaks)} break(s); first at seq "
                                    f"{breaks[0].seq} ({breaks[0].kind})"))

    # 2. completeness
    acts = actions(root)
    rep.actions_total = len(acts)
    need = {"intent", "decision", "execution"}
    for aid, stages in acts.items():
        missing = need - set(stages)
        if not missing:
            continue
        if "decision" in missing and "execution" in stages:
            # The serious one: something ran without the gate recording a verdict.
            rep.findings.append(Finding(
                "fail", "action.ungated",
                f"{aid[:12]}… executed with no DECISION record"))
        elif missing == {"execution"}:
            rep.findings.append(Finding(
                "warn", "action.dangling",
                f"{aid[:12]}… was intended and decided but never completed"))
        else:
            rep.findings.append(Finding(
                "warn", "action.incomplete",
                f"{aid[:12]}… missing {', '.join(sorted(missing))}"))

    # A refusal that ran anyway. This is the check that catches a gate which
    # reports denials it does not actually impose — the failure mode where the
    # ledger looks strictest exactly where it is weakest, because every blocked
    # action is recorded and none of them were blocked.
    for aid, stages in acts.items():
        d, e = stages.get("decision"), stages.get("execution")
        if not (d and e):
            continue
        verdict = d.payload.get("verdict")
        status = e.payload.get("status")
        if verdict in ("deny", "hold") and status not in ("blocked", "error"):
            rep.findings.append(Finding(
                "fail", "decision.not_enforced",
                f"{aid[:12]}… was recorded {verdict} but executed with "
                f"status={status} — the verdict was advisory"))

    # Ordering: a DECISION that predates its INTENT is not a race, it is a
    # record written to fit a story already told.
    for aid, stages in acts.items():
        i, d, e = stages.get("intent"), stages.get("decision"), stages.get("execution")
        if i and d and d.seq < i.seq:
            rep.findings.append(Finding("fail", "stage.out_of_order",
                                        f"{aid[:12]}… DECISION precedes INTENT"))
        if d and e and e.seq < d.seq:
            rep.findings.append(Finding("fail", "stage.out_of_order",
                                        f"{aid[:12]}… EXECUTION precedes DECISION"))

    # 3. coverage
    ok_anchors = [a for a in anchor_mod.anchors(root) if a.status in ("ok", "pending")]
    rep.anchored_seq = max((a.seq for a in ok_anchors), default=-1)
    if not ok_anchors:
        rep.findings.append(Finding(
            "warn", "anchor.none",
            "no timestamp anchors — the chain is self-consistent but its age "
            "rests entirely on this repository's own word"))
    elif rep.unanchored:
        rep.findings.append(Finding(
            "warn", "anchor.lag",
            f"{rep.unanchored} record(s) written since the last anchor at seq "
            f"{rep.anchored_seq}"))
    else:
        rep.findings.append(Finding("ok", "anchor.current",
                                    f"head seq {rep.head_seq} is anchored"))

    if check_anchors:
        for a in ok_anchors:
            if a.kind == "rfc3161":
                good, detail = anchor_mod.verify_rfc3161(root, a)
            else:
                good, detail = anchor_mod.verify_ots(root, a)
            rep.findings.append(Finding(
                "ok" if good else "warn", f"anchor.{a.kind}",
                f"seq {a.seq}: {detail}"))

    # 4. oversight
    appr = approvals(root)
    for aid, entry in appr.items():
        stages = acts.get(aid, {})
        actor = stages["intent"].actor if "intent" in stages else "?"
        if entry.get("approver") == actor:
            rep.findings.append(Finding(
                "fail", "oversight.self_approved",
                f"{aid[:12]}… was approved by the same identity that raised it "
                f"({actor})"))

    return rep


def format_report(rep: Report) -> str:
    """Plain text, for CI logs and for anyone without the CLI."""
    icon = {"ok": "PASS", "warn": "WARN", "fail": "FAIL"}
    lines = [
        "AI governance provenance report",
        "=" * 60,
        f"records          {rep.records}",
        f"actions          {rep.actions_total}",
        f"head sequence    {rep.head_seq}",
        f"anchored through {rep.anchored_seq}"
        + (f"  ({rep.unanchored} unanchored)" if rep.unanchored else ""),
        "",
    ]
    for f in rep.findings:
        lines.append(f"  [{icon[f.level]}] {f.code:<26} {f.detail}")
    if rep.breaks:
        lines += ["", "chain breaks:"]
        for b in rep.breaks[:20]:
            lines.append(f"  seq {b.seq:<8} {b.kind:<10} {b.detail}")
        if len(rep.breaks) > 20:
            lines.append(f"  … {len(rep.breaks) - 20} more")
    lines += ["", f"RESULT: {'OK' if rep.ok else 'FAILED'}"]
    return "\n".join(lines)
