"""Stage 05 — TIMESTAMP. RFC 3161 for minutes, OpenTimestamps for decades.

A hash chain proves nobody edited the middle without editing the end. It says
nothing about *when* the end existed, and it cannot: every byte of it is ours,
so a full rewrite produces a perfectly consistent chain. Anchoring is what
removes us from the trust set — a signature over the head hash, made by someone
with no stake in our story.

Two anchors, because they fail differently:

  **RFC 3161** — a Time Stamping Authority signs `(hash, time)` within seconds.
  Cheap, immediate, legally recognised. Trust is the TSA's key: if that key is
  compromised or the authority disappears with its certificate, an old token
  becomes unverifiable.

  **OpenTimestamps** — the hash is aggregated into a Bitcoin transaction. Free,
  needs no trusted party at all, and stays verifiable as long as the chain does.
  Costs hours for confirmation, so it can never be the only anchor.

Together: the RFC 3161 token answers "was this here this morning" today, and the
Bitcoin attestation answers it in twenty years when the TSA is gone.

## Why anchoring is not in the hook

Both anchors need the network. A PreToolUse hook that makes a network call adds
its latency and its failure modes to every single tool call the agent makes —
and a TSA that is slow would make the agent look slow, while a TSA that is down
would (fail-closed) stop work entirely or (fail-open) silently record nothing.

So the hot path only ever appends locally, and anchoring runs separately over
whatever the head is at the time — `pf provenance anchor`, from a scheduler or
from CI. Anchoring the head anchors every record beneath it, so batching costs
no coverage: one token per hour proves everything written in that hour existed
by then. The window of un-anchored records is the exposure, and it is reported
by `pf provenance status` rather than assumed to be zero.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path

from pf.provenance.chain import chain_dir, head
from pf.provenance.record import now

ANCHORS_NAME = "anchors.jsonl"
TOKEN_DIR = "anchors"

#: Public, free, no account. Overridable with PF_TSA_URL — an organisation with
#: a qualified TSA (eIDAS, or an internal one) should point at it, since the
#: evidentiary weight of the token is entirely the authority's.
DEFAULT_TSA = os.environ.get("PF_TSA_URL", "https://freetsa.org/tsr")

SHA256_OID_DER = bytes([0x06, 0x09, 0x60, 0x86, 0x48, 0x01,
                        0x65, 0x03, 0x04, 0x02, 0x01])


# --------------------------------------------------------------------------
# Minimal DER. Deliberately hand-rolled: a TimeStampReq is four nested values,
# and adding an ASN.1 dependency to the platform's base install to build them
# would cost more than it saves. Parsing is limited to reading the response
# status — anything beyond that is openssl's job, below.
# --------------------------------------------------------------------------

def _der_len(n: int) -> bytes:
    if n < 0x80:
        return bytes([n])
    body = n.to_bytes((n.bit_length() + 7) // 8, "big")
    return bytes([0x80 | len(body)]) + body


def _tlv(tag: int, content: bytes) -> bytes:
    return bytes([tag]) + _der_len(len(content)) + content


def _int(value: int) -> bytes:
    if value == 0:
        return _tlv(0x02, b"\x00")
    body = value.to_bytes((value.bit_length() + 8) // 8, "big")
    # DER integers are signed; a leading bit of 1 would read as negative.
    return _tlv(0x02, body.lstrip(b"\x00") if body[0] == 0 and len(body) > 1
                and body[1] < 0x80 else body)


def build_request(digest_hex: str, *, nonce: int | None = None,
                  cert_req: bool = True) -> bytes:
    """A DER TimeStampReq over `digest_hex`.

    `cert_req=True` asks the TSA to embed its certificate chain in the reply.
    Without it the token verifies only for someone who already has that
    certificate — which is the opposite of "verifiable by anyone", so it
    defaults on despite the larger token.
    """
    raw = bytes.fromhex(digest_hex)
    if len(raw) != 32:
        raise ValueError(f"expected a 32-byte SHA-256 digest, got {len(raw)}")

    algorithm = _tlv(0x30, SHA256_OID_DER + _tlv(0x05, b""))   # AlgorithmIdentifier
    imprint = _tlv(0x30, algorithm + _tlv(0x04, raw))          # MessageImprint

    parts = _int(1) + imprint                                   # version, imprint
    if nonce is None:
        nonce = int.from_bytes(os.urandom(8), "big")
    # The nonce is what makes a reply provably fresh rather than replayed from
    # a cache: the TSA must echo it, so a recorded response cannot be reused.
    parts += _int(nonce)
    if cert_req:
        parts += _tlv(0x01, b"\xff")
    return _tlv(0x30, parts)


def _read_status(der: bytes) -> tuple[int, str]:
    """PKIStatus from a TimeStampResp. 0 granted, 1 granted-with-mods.

    Walks only as far as the first INTEGER inside the first nested SEQUENCE,
    which is where PKIStatusInfo.status sits. Anything deeper is left to
    openssl rather than reimplemented.
    """
    try:
        if not der or der[0] != 0x30:
            return -1, "response is not a DER SEQUENCE"
        i = 1
        # Skip the outer length.
        if der[i] & 0x80:
            i += 1 + (der[i] & 0x7F)
        else:
            i += 1
        if der[i] != 0x30:
            return -1, "no PKIStatusInfo"
        i += 1
        if der[i] & 0x80:
            i += 1 + (der[i] & 0x7F)
        else:
            i += 1
        if der[i] != 0x02:
            return -1, "no status INTEGER"
        ln = der[i + 1]
        status = int.from_bytes(der[i + 2:i + 2 + ln], "big")
        return status, {0: "granted", 1: "granted with mods"}.get(status, "rejected")
    except (IndexError, ValueError) as exc:
        return -1, f"unparseable response: {exc}"


@dataclass(frozen=True)
class Anchor:
    """One proof that a chain head existed before a point in time."""

    ts: str
    seq: int              # chain head sequence this anchor covers
    head_hash: str
    kind: str             # rfc3161 | opentimestamps
    status: str           # ok | pending | failed
    path: str             # token file, relative to the provenance dir
    detail: str = ""


def _record(root: Path, anchor: Anchor) -> Anchor:
    d = chain_dir(root)
    d.mkdir(parents=True, exist_ok=True)
    with (d / ANCHORS_NAME).open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(asdict(anchor), sort_keys=True,
                            separators=(",", ":")) + "\n")
    return anchor


def anchors(root: Path) -> list[Anchor]:
    p = chain_dir(root) / ANCHORS_NAME
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            out.append(Anchor(**json.loads(line)))
    return out


def stamp_rfc3161(root: Path, *, url: str = DEFAULT_TSA,
                  timeout: int = 20) -> Anchor:
    """Get a signed timestamp over the current chain head."""
    h = head(root)
    if h.seq < 0:
        return Anchor(now(), -1, h.hash, "rfc3161", "failed", "",
                      "chain is empty — nothing to anchor")

    d = chain_dir(root) / TOKEN_DIR
    d.mkdir(parents=True, exist_ok=True)
    rel = f"{TOKEN_DIR}/{h.seq:012d}.tsr"
    out = chain_dir(root) / rel

    req = urllib.request.Request(
        url, data=build_request(h.hash),
        headers={"Content-Type": "application/timestamp-query",
                 "Accept": "application/timestamp-reply"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
    except (urllib.error.URLError, OSError, TimeoutError) as exc:
        # A TSA being unreachable is an operational fact, not a crash: the
        # chain is unharmed and the next run anchors a later head, which
        # covers everything this one would have.
        return _record(root, Anchor(now(), h.seq, h.hash, "rfc3161", "failed",
                                    "", f"{type(exc).__name__}: {exc}"))

    status, label = _read_status(body)
    if status not in (0, 1):
        return _record(root, Anchor(now(), h.seq, h.hash, "rfc3161", "failed",
                                    "", f"TSA said: {label}"))

    out.write_bytes(body)
    return _record(root, Anchor(now(), h.seq, h.hash, "rfc3161", "ok", rel,
                                f"{url} ({label})"))


def verify_rfc3161(root: Path, anchor: Anchor, *,
                   ca_file: str | None = None) -> tuple[bool, str]:
    """Check a stored token against the head it claims to cover.

    Signature verification is delegated to `openssl ts -verify` rather than
    reimplemented. The point of this stage is that a third party can check the
    proof with standard tools; shelling out to the same tool they would use
    keeps our verdict and theirs the same verdict.
    """
    token = chain_dir(root) / anchor.path
    if not token.exists():
        return False, f"token missing: {anchor.path}"
    if not shutil.which("openssl"):
        return False, ("openssl not installed — token stored but unverified "
                       "(install openssl, or verify elsewhere with the .tsr)")

    ca = ca_file or os.environ.get("PF_TSA_CA")
    cmd = ["openssl", "ts", "-verify", "-digest", anchor.head_hash,
           "-in", str(token)]
    cmd += ["-CAfile", ca] if ca else ["-no_check_time"]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode == 0:
        return True, "openssl: verification OK"
    err = (proc.stderr or proc.stdout).strip().splitlines()
    detail = err[-1] if err else f"exit {proc.returncode}"
    if not ca:
        detail += (" — no CA file; set PF_TSA_CA to the TSA root to check the "
                   "signature chain")
    return False, detail


def stamp_ots(root: Path) -> Anchor:
    """Submit the head hash to OpenTimestamps calendars.

    Returns `pending`: the `.ots` receipt is a promise that the hash is queued
    for the next Bitcoin block aggregation. It becomes a real proof only after
    `upgrade_ots` fetches the confirmed attestation, typically hours later.
    Reporting it as `ok` at submission time would overstate the evidence.
    """
    h = head(root)
    if h.seq < 0:
        return Anchor(now(), -1, h.hash, "opentimestamps", "failed", "",
                      "chain is empty — nothing to anchor")
    if not shutil.which("ots"):
        return Anchor(now(), h.seq, h.hash, "opentimestamps", "failed", "",
                      "ots client not installed (pip install opentimestamps-client)")

    d = chain_dir(root) / TOKEN_DIR
    d.mkdir(parents=True, exist_ok=True)
    stem = d / f"{h.seq:012d}.head"
    # `ots stamp` timestamps a *file*, so the head hash is written to one. The
    # file's own SHA-256 is what gets stamped, and it is not the head hash —
    # so the detail line records both, and verification checks the file's
    # content is still exactly the head it claims.
    stem.write_text(h.hash, encoding="utf-8")
    proc = subprocess.run(["ots", "stamp", str(stem)],
                          capture_output=True, text=True)
    rel = f"{TOKEN_DIR}/{stem.name}.ots"
    if proc.returncode != 0 or not (chain_dir(root) / rel).exists():
        return _record(root, Anchor(now(), h.seq, h.hash, "opentimestamps",
                                    "failed", "",
                                    (proc.stderr or proc.stdout).strip()[:300]))
    return _record(root, Anchor(now(), h.seq, h.hash, "opentimestamps",
                                "pending", rel,
                                "submitted to calendars; run `pf provenance "
                                "upgrade` once a block has confirmed"))


def upgrade_ots(root: Path, anchor: Anchor) -> tuple[bool, str]:
    """Turn a pending receipt into a confirmed Bitcoin attestation."""
    if not shutil.which("ots"):
        return False, "ots client not installed"
    token = chain_dir(root) / anchor.path
    if not token.exists():
        return False, f"receipt missing: {anchor.path}"
    proc = subprocess.run(["ots", "upgrade", str(token)],
                          capture_output=True, text=True)
    text = (proc.stderr or proc.stdout).strip()
    if proc.returncode != 0:
        return False, text[:300]
    return True, text[:300] or "upgraded"


def verify_ots(root: Path, anchor: Anchor) -> tuple[bool, str]:
    if not shutil.which("ots"):
        return False, "ots client not installed"
    token = chain_dir(root) / anchor.path
    stamped = token.with_suffix("")     # the .head file the .ots covers
    if not token.exists() or not stamped.exists():
        return False, f"receipt or stamped file missing: {anchor.path}"
    # The receipt proves *this file* existed. If its content is no longer the
    # head it was written for, the proof is real but it proves something else.
    if stamped.read_text(encoding="utf-8").strip() != anchor.head_hash:
        return False, "stamped file no longer holds the head hash it recorded"
    proc = subprocess.run(["ots", "verify", str(token)],
                          capture_output=True, text=True)
    text = (proc.stderr or proc.stdout).strip()
    ok = (proc.returncode == 0 and "Success" in text) or "as of" in text
    return ok, text[:300]
