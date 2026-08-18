"""The five stages of an agent action, and the bytes they hash to.

An action is not one event. It is five, and the split is the whole point: a
system that records only what happened cannot answer whether what happened was
what was *meant* to happen, or whether anything checked.

    01 INTENT      what the agent proposed, written BEFORE the action
    02 DECISION    the policy gate's verdict on that intent
    03 EXECUTION   what actually happened, written AFTER the action
    04 CHAIN       each record carries the hash of the one before it
    05 TIMESTAMP   the chain head is anchored to time nobody here controls

Stages 01–03 are records in this module. Stage 04 is `pf.provenance.chain`,
stage 05 is `pf.provenance.anchor`. They are numbered because the order is
load-bearing: an INTENT written after the fact is a story, and a DECISION
written after the EXECUTION is a rationalisation.

## Why canonical bytes matter more than the schema

"Verifiable by anyone" means a third party recomputes our hashes and gets our
numbers, using nothing of ours but the record. That only holds if the bytes a
record hashes to are a function of its *content* and not of the writer — so
serialisation is pinned here rather than left to `json.dumps` defaults:

  * keys sorted, so field order in a dataclass never changes a hash
  * no whitespace, so a pretty-printer cannot silently break the chain
  * `ensure_ascii=False` with explicit UTF-8, so a non-ASCII project name
    hashes to the same bytes whichever writer produced it
  * floats are refused outright — 0.1 does not round-trip identically across
    languages, and a verifier written in Go must reach our digest

This is RFC 8785 (JCS) in the subset we allow. We do not import a JCS library
because the verifier must be re-implementable in an afternoon, in any language,
by someone who does not trust us. A dependency they also have to trust defeats
that.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal

#: The three recorded stages. CHAIN and TIMESTAMP are properties *of* records,
#: not records themselves, which is why they are not in this enum.
Stage = Literal["intent", "decision", "execution"]

STAGES: tuple[Stage, ...] = ("intent", "decision", "execution")

#: `prev` of the first record. Not a hash of anything — a fixed origin, so a
#: chain that has been truncated to look like a fresh one is still detectable
#: (a genesis record with seq != 0 is a forgery).
GENESIS = "0" * 64

HASH_NAME = "sha256"


class NonCanonical(ValueError):
    """A value that cannot be hashed reproducibly across implementations."""


def _check(value: Any, path: str = "$") -> None:
    """Reject anything whose JSON encoding is implementation-dependent.

    Floats are the reason this exists. `json.dumps(0.1)` is "0.1" in CPython
    and the shortest round-trip in most languages, but not all, and a digest
    that disagrees across languages is not a digest anyone else can check.
    Callers that need a number with a fraction send it as a string and say what
    the units are.
    """
    if isinstance(value, float):
        raise NonCanonical(
            f"{path}: float is not canonical — send a string, or an int of a "
            f"fixed unit (cents, milliseconds, bytes)")
    if isinstance(value, dict):
        for k, v in value.items():
            if not isinstance(k, str):
                raise NonCanonical(f"{path}: non-string key {k!r}")
            _check(v, f"{path}.{k}")
    elif isinstance(value, (list, tuple)):
        for i, v in enumerate(value):
            _check(v, f"{path}[{i}]")
    elif not isinstance(value, (str, int, bool, type(None))):
        raise NonCanonical(f"{path}: {type(value).__name__} is not JSON-canonical")


def canonical_bytes(obj: dict[str, Any]) -> bytes:
    """The exact bytes a record hashes to. Reimplementable in any language."""
    _check(obj)
    return json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def digest(obj: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_bytes(obj)).hexdigest()


def now() -> str:
    """RFC 3339 UTC, whole seconds.

    Sub-second precision is dropped deliberately: it varies with the clock
    source, it is not meaningful for ordering (that is what `seq` is for), and
    it is one more thing a verifier has to reproduce exactly.
    """
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass(frozen=True)
class Record:
    """One stage of one action, linked to the stage before it.

    `action_id` is what makes the five stages one story: INTENT, DECISION and
    EXECUTION for a single tool call share it, so an audit reads "this was
    proposed, this was decided, this happened" rather than three unrelated
    rows. A DECISION with no matching INTENT, or an EXECUTION with no matching
    DECISION, is exactly the gap `pf provenance verify` reports.
    """

    seq: int
    action_id: str
    stage: Stage
    ts: str
    actor: str
    session: str
    group: str
    project: str
    tool: str
    target: str
    payload: dict[str, Any] = field(default_factory=dict)
    prev: str = GENESIS
    hash: str = ""

    def unhashed(self) -> dict[str, Any]:
        """Everything the hash covers — i.e. the record minus the hash itself."""
        d = asdict(self)
        d.pop("hash", None)
        return d

    def sealed(self) -> Record:
        """This record with `hash` computed over every other field.

        Note `prev` is inside the digest. That is what makes the structure a
        chain rather than a list of independently-signed rows: altering an old
        record changes its hash, which is the `prev` of the next one, which
        changes that one's hash, and so on to the head — and the head is what
        the timestamp authority signed.
        """
        from dataclasses import replace

        return replace(self, hash=digest(self.unhashed()))

    def verify_self(self) -> bool:
        return bool(self.hash) and self.hash == digest(self.unhashed())

    def to_json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False)

    @staticmethod
    def from_dict(d: dict[str, Any]) -> Record:
        known = set(Record.__dataclass_fields__)
        return Record(**{k: v for k, v in d.items() if k in known})
