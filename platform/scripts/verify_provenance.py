#!/usr/bin/env python3
"""Standalone verifier for an agent-action provenance chain.

    python3 verify_provenance.py <provenance-dir>

Stdlib only. No install, no network, no dependency on the platform that wrote
the chain — which is the point. "Verifiable by anyone" is a property of the
evidence, not a feature of our CLI, and a verifier you have to trust us to
supply verifies nothing. This file is ~150 lines and re-implementable in any
language from the spec in the docstring below.

`pf provenance export` ships a copy of this script next to the chain it exports,
so an auditor receives the evidence and the means to check it in one bundle.

## The spec, in full

A chain is a JSONL file, one record per line, each a JSON object with:

    seq        int    0-based, contiguous, ascending
    action_id  str    shared by the intent/decision/execution of one action
    stage      str    "intent" | "decision" | "execution"
    ts         str    RFC 3339 UTC, whole seconds
    actor      str
    session    str
    group      str
    project    str
    tool       str
    target     str
    payload    obj
    prev       str    hex sha256 of the previous record's `hash`
                      (64 zeros for seq 0)
    hash       str    hex sha256 of this record's canonical bytes

Canonical bytes = JSON of the record *without* the `hash` key, with:
  - keys sorted lexicographically at every level
  - separators "," and ":" (no whitespace)
  - non-ASCII emitted literally, encoded UTF-8
  - no floats anywhere (they do not round-trip identically across languages)

Verification is then: for each record, recompute the digest and compare to
`hash`; compare `prev` to the previous record's `hash`; check `seq` is the
previous `seq` + 1.

Exit 0 if the chain verifies, 1 if it does not.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

GENESIS = "0" * 64


def canonical_bytes(obj: dict) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def digest(record: dict) -> str:
    body = {k: v for k, v in record.items() if k != "hash"}
    return hashlib.sha256(canonical_bytes(body)).hexdigest()


def verify_chain(path: Path) -> tuple[bool, list[str], list[dict]]:
    problems: list[str] = []
    records: list[dict] = []
    prev_hash, expect_seq = GENESIS, 0

    with path.open(encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError as exc:
                problems.append(f"line {lineno}: not valid JSON ({exc})")
                return False, problems, records
            records.append(rec)

            if rec.get("seq") != expect_seq:
                problems.append(
                    f"line {lineno}: seq is {rec.get('seq')}, expected {expect_seq} "
                    f"— a record was inserted or removed")
            if rec.get("prev") != prev_hash:
                problems.append(
                    f"seq {rec.get('seq')}: prev={str(rec.get('prev'))[:12]}… but the "
                    f"previous record hashes to {prev_hash[:12]}… — the chain was cut")
            recomputed = digest(rec)
            if rec.get("hash") != recomputed:
                problems.append(
                    f"seq {rec.get('seq')}: content hashes to {recomputed[:12]}… but "
                    f"the record claims {str(rec.get('hash'))[:12]}… — it was edited")

            prev_hash = rec.get("hash", "")
            expect_seq = rec.get("seq", expect_seq) + 1

    return not problems, problems, records


def check_completeness(records: list[dict]) -> list[str]:
    """An EXECUTION with no DECISION is work that never passed the gate."""
    stages: dict[str, set[str]] = {}
    for r in records:
        stages.setdefault(r.get("action_id", "?"), set()).add(r.get("stage", "?"))
    out = []
    for aid, seen in sorted(stages.items()):
        missing = {"intent", "decision", "execution"} - seen
        if "decision" in missing and "execution" in seen:
            out.append(f"action {aid[:12]}…: EXECUTED WITHOUT A RECORDED DECISION")
        elif missing:
            out.append(f"action {aid[:12]}…: missing {', '.join(sorted(missing))}")
    return out


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__.split("## The spec")[0].strip())
        return 2
    d = Path(argv[1])
    chain = d / "chain.jsonl" if d.is_dir() else d
    if not chain.exists():
        print(f"no chain at {chain}")
        return 2

    ok, problems, records = verify_chain(chain)
    gaps = check_completeness(records)

    print(f"chain     {chain}")
    print(f"records   {len(records)}")
    if records:
        print(f"head      seq {records[-1].get('seq')} "
              f"{str(records[-1].get('hash'))[:16]}…")

    anchors = (d / "anchors.jsonl") if d.is_dir() else None
    if anchors and anchors.exists():
        lines = [json.loads(x) for x in anchors.read_text().splitlines() if x.strip()]
        good = [a for a in lines if a.get("status") in ("ok", "pending")]
        covered = max((a.get("seq", -1) for a in good), default=-1)
        print(f"anchors   {len(good)} usable, covering up to seq {covered}")
        for a in good:
            print(f"          {a.get('kind')} seq {a.get('seq')} -> {a.get('path')}")
        print("          verify an RFC 3161 token independently with:")
        print("            openssl ts -verify -digest <head-hash> -in <token.tsr> "
              "-CAfile <tsa-ca.pem>")
        print("          verify an OpenTimestamps receipt with:  ots verify <file.ots>")
    else:
        print("anchors   none — the chain is internally consistent, but nothing "
              "independent attests to when it existed")

    print()
    if problems:
        print(f"INTEGRITY: FAILED ({len(problems)} problem(s))")
        for p in problems[:40]:
            print(f"  - {p}")
        if len(problems) > 40:
            print(f"  … {len(problems) - 40} more")
    else:
        print("INTEGRITY: OK — every record hashes to its digest and links to "
              "its predecessor")

    if gaps:
        print(f"\nCOMPLETENESS: {len(gaps)} gap(s)")
        for g in gaps[:40]:
            print(f"  - {g}")
    else:
        print("COMPLETENESS: OK — every action has intent, decision and execution")

    return 0 if ok and not gaps else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
