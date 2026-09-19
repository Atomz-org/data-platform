"""Agent action provenance: five stages, one chain, verifiable by anyone.

    01 INTENT      before the action        ledger.intent
    02 DECISION    policy gate              ledger.decision
    03 EXECUTION   after the action         ledger.execution
    04 CHAIN       SHA-256                  chain.append / chain.verify
    05 TIMESTAMP   RFC 3161 + OTS           anchor.stamp_rfc3161 / stamp_ots

The primary architecture for AI governance in this platform: nothing an agent
does is a bare side effect. Every action is proposed, gated, performed and
linked, and the link is anchored to time this repository does not control.

Callers want `action()` — it writes stages 01–03 in the right order and cannot
be made to write them in the wrong one. Everything else here exists for the
hooks, the CLI and the auditor.

`pf provenance verify` is the audit; `provenance/verify_chain.py` is the same
audit as a standalone stdlib script, for someone who has the ledger but not
this package and no reason to trust it.
"""

from pf.provenance.anchor import (
    Anchor,
    anchors,
    stamp_ots,
    stamp_rfc3161,
    upgrade_ots,
    verify_ots,
    verify_rfc3161,
)
from pf.provenance.audit import Finding, Report, format_report, report
from pf.provenance.chain import Break, Head, append, head, read_all
from pf.provenance.chain import verify as verify_chain
from pf.provenance.ledger import (
    NotRecorded,
    Revoked,
    action,
    actions,
    approvals,
    approve,
    dangling,
    decision,
    enforcing,
    execution,
    intent,
    is_approved,
    is_revoked,
    new_action_id,
    reinstate,
    revoke,
)
from pf.provenance.record import GENESIS, STAGES, Record, Stage, canonical_bytes, digest

__all__ = [
    "GENESIS",
    "STAGES",
    "Anchor",
    "Break",
    "Finding",
    "Head",
    "NotRecorded",
    "Record",
    "Report",
    "Revoked",
    "Stage",
    "action",
    "actions",
    "anchors",
    "append",
    "approvals",
    "approve",
    "canonical_bytes",
    "dangling",
    "decision",
    "digest",
    "enforcing",
    "execution",
    "format_report",
    "head",
    "intent",
    "is_approved",
    "is_revoked",
    "new_action_id",
    "read_all",
    "reinstate",
    "report",
    "revoke",
    "stamp_ots",
    "stamp_rfc3161",
    "upgrade_ots",
    "verify_chain",
    "verify_ots",
    "verify_rfc3161",
]
