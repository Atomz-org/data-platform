"""Stage 04 — CHAIN. Append-only, tamper-evident, SHA-256 linked.

The file is JSONL and that is a deliberate choice over a database. An auditor
with `sha256sum` and `python -c` must be able to check it, and a DuckDB file
requires DuckDB to read. The database mirror in `pf.provenance.ledger` exists
for querying; this file is the evidence.

## What the chain does and does not prove

It proves *internal consistency*: record N's hash covers record N-1's hash, so
editing any record invalidates every record after it. Anyone who can rewrite
the whole file can still produce a self-consistent chain — which is why stage
05 exists. A timestamp over the head hash means a rewrite has to also forge a
signature from a party that is not us. The chain alone is tamper-*evident* to
anyone holding an earlier head; the anchor is what makes it evident to someone
who has only ever seen the file once.

## Why the lock

Claude Code fires PreToolUse and PostToolUse hooks per tool call, and parallel
tool calls mean two processes can reach `append()` at the same instant. Without
a lock both read the same head, both write `prev = H`, and the chain forks —
which reads to a verifier as tampering rather than as a race. `flock` over the
whole read-head-then-write is what makes the sequence a total order.

Append is O(1): the head is cached in a sidecar file rather than re-read from
the tail of the chain, so a hook on a million-record ledger costs the same as
on an empty one. `verify()` is the O(n) pass, and it is not on the hot path.
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pf.provenance.record import GENESIS, Record

try:  # POSIX only; Windows falls back to no locking (see _locked).
    import fcntl
except ImportError:  # pragma: no cover - platform dependent
    fcntl = None  # type: ignore[assignment]

CHAIN_NAME = "chain.jsonl"
HEAD_NAME = "head.json"
LOCK_NAME = ".lock"


def chain_dir(root: Path) -> Path:
    return Path(root) / "provenance"


@dataclass(frozen=True)
class Head:
    """The tip of the chain: what the next record must point at."""

    seq: int
    hash: str

    @property
    def next_seq(self) -> int:
        return self.seq + 1


EMPTY = Head(seq=-1, hash=GENESIS)


@contextmanager
def _locked(d: Path) -> Iterator[None]:
    """Exclusive lock for the whole read-modify-write.

    A separate lock file rather than locking the chain itself: locking the file
    you are appending to means the lock disappears with any rotation of it, and
    an fd opened for append cannot be locked before it exists.
    """
    d.mkdir(parents=True, exist_ok=True)
    lock = d / LOCK_NAME
    if fcntl is None:  # pragma: no cover - non-POSIX
        yield
        return
    with lock.open("w") as fh:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)


def _read_head(d: Path) -> Head:
    """Cached head, falling back to a scan when the sidecar is missing or stale.

    The sidecar can legitimately be absent (first run) or wrong (someone copied
    a chain without it). Trusting it blindly would let a deleted sidecar reset
    the chain to genesis and orphan every existing record, so a missing file
    means "go and look", not "start over".
    """
    p = d / HEAD_NAME
    if p.exists():
        try:
            raw = json.loads(p.read_text())
            return Head(seq=int(raw["seq"]), hash=str(raw["hash"]))
        except (json.JSONDecodeError, KeyError, ValueError, TypeError):
            pass
    return _scan_head(d)


def _scan_head(d: Path) -> Head:
    chain = d / CHAIN_NAME
    if not chain.exists():
        return EMPTY
    last: dict[str, Any] | None = None
    with chain.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    last = json.loads(line)
                except json.JSONDecodeError:
                    continue
    if last is None:
        return EMPTY
    return Head(seq=int(last["seq"]), hash=str(last["hash"]))


def _write_head(d: Path, head: Head) -> None:
    """Write the sidecar atomically.

    A torn head file is recoverable (the scan above), but a torn one that still
    parses is not — it would hand out a stale `prev` and fork the chain. Rename
    is atomic on POSIX, so the file is either the old head or the new one.
    """
    tmp = d / f"{HEAD_NAME}.tmp"
    tmp.write_text(json.dumps({"seq": head.seq, "hash": head.hash}), encoding="utf-8")
    tmp.replace(d / HEAD_NAME)


def head(root: Path) -> Head:
    """The current tip, without taking the write lock."""
    return _read_head(chain_dir(root))


def append(root: Path, record: Record) -> Record:
    """Seal `record` onto the chain and return it with `seq`, `prev` and `hash`.

    The caller's `seq` and `prev` are ignored — they are assigned here, under
    the lock, because they are properties of the chain rather than of the event.
    """
    from dataclasses import replace

    d = chain_dir(root)
    with _locked(d):
        h = _read_head(d)
        sealed = replace(record, seq=h.next_seq, prev=h.hash).sealed()
        # Append and flush *before* the head moves. If the process dies between
        # the two, the sidecar is stale-but-behind and the scan fallback
        # recovers the true tip. The reverse order would advertise a head for a
        # record that was never written.
        with (d / CHAIN_NAME).open("a", encoding="utf-8") as fh:
            fh.write(sealed.to_json() + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        _write_head(d, Head(seq=sealed.seq, hash=sealed.hash))
    return sealed


def read_all(root: Path) -> list[Record]:
    chain = chain_dir(root) / CHAIN_NAME
    if not chain.exists():
        return []
    out: list[Record] = []
    with chain.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(Record.from_dict(json.loads(line)))
    return out


@dataclass(frozen=True)
class Break:
    """One place the chain stops being self-consistent."""

    seq: int
    kind: str          # hash | link | sequence | parse
    detail: str


def verify(root: Path) -> tuple[bool, list[Break]]:
    """Recompute every hash and every link. This is the whole audit.

    Deliberately does not stop at the first break: an auditor needs to know
    whether one record was edited or the file was rewritten from some point on,
    and that is the difference between one `hash` break and a run of them.
    """
    breaks: list[Break] = []
    chain = chain_dir(root) / CHAIN_NAME
    if not chain.exists():
        return True, []

    prev_hash = GENESIS
    expect_seq = 0
    with chain.open(encoding="utf-8") as fh:
        for lineno, line in enumerate(fh):
            line = line.strip()
            if not line:
                continue
            try:
                rec = Record.from_dict(json.loads(line))
            except (json.JSONDecodeError, TypeError) as exc:
                breaks.append(Break(lineno, "parse", str(exc)))
                return False, breaks

            if rec.seq != expect_seq:
                breaks.append(Break(rec.seq, "sequence",
                                    f"expected seq {expect_seq}, found {rec.seq}"))
            if rec.prev != prev_hash:
                breaks.append(Break(rec.seq, "link",
                                    f"prev is {rec.prev[:12]}…, "
                                    f"predecessor hashes to {prev_hash[:12]}…"))
            if not rec.verify_self():
                breaks.append(Break(rec.seq, "hash",
                                    "record does not hash to its stated digest — "
                                    "content was altered after it was written"))
            prev_hash = rec.hash
            expect_seq = rec.seq + 1

    return not breaks, breaks
