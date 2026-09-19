# Agent action provenance

The primary architecture for AI governance here. Nothing an agent does is a bare
side effect: every action is proposed, gated, performed, linked, and anchored to
time this repository does not control.

```
01  INTENT      what was proposed        written BEFORE the action
02  DECISION    the policy gate's verdict
03  EXECUTION   what actually happened   written AFTER the action
04  CHAIN       SHA-256, each record carrying the hash of the one before
05  TIMESTAMP   RFC 3161 + OpenTimestamps over the chain head
```

The order is the guarantee. An INTENT written after the fact is a story, and a
DECISION written after the EXECUTION is a rationalisation.

## Why five stages and not one log line

A log says what happened. It cannot answer the two questions an incident
actually turns on:

- **Was this what the agent meant to do?** That needs a record written before
  the action, by a process that did not yet know the outcome.
- **Did anything check?** That needs the gate's verdict recorded whether it
  allowed or denied. A ledger holding only refusals proves the gate can say no;
  it cannot show the gate was consulted for the action that caused the incident.

Stages 04 and 05 exist because the first three are ours. A chain proves nobody
edited the middle without editing the end; an anchor proves when the end
existed, signed by someone with no stake in our story.

## Where it runs

| Path | Stage 01–02 | Stage 03 |
|---|---|---|
| Claude Code tool calls | `platform/hooks/pre_tool_use.py` | `platform/hooks/post_tool_use.py` |
| Programmatic LLM calls | `pf.agents.base.call` | same function |
| Anything else | `pf.provenance.action()` | same context manager |

`action()` is the preferred API because it cannot be made to write the stages in
the wrong order, and it writes EXECUTION even when the body raises:

```python
from pf.provenance import action

with action(root, tool="dbt", target="model.orders", summary="rebuild") as a:
    a["detail"] = run_model()
```

Tool calls are recorded for mutating tools only — `Edit`, `Write`, `MultiEdit`,
`NotebookEdit`, `Bash`. A chain in which every file read is an action buries the
writes that matter. `PF_PROVENANCE_SCOPE=all` records everything.

## Commands

```
pf provenance status              head, anchor coverage, kill-switch state
pf provenance log -n 20           recent actions as the chain recorded them
pf provenance verify              the audit; non-zero exit on a failure
pf provenance verify --anchors    also check the timestamp tokens
pf provenance anchor --kind both  timestamp the head (RFC 3161 + OTS)
pf provenance upgrade             fetch confirmed Bitcoin attestations
pf provenance revoke <actor>      kill switch
pf provenance approve <action>    record human approval of a held action
pf provenance export <dir>        evidence bundle for an auditor
pf provenance sync                mirror the chain into DuckDB for querying
```

## What the audit checks

`pf provenance verify` is the blocking check in CI. Four questions, in order of
what they can prove:

1. **Integrity** — every record hashes to its digest, every `prev` links.
2. **Completeness** — every action has all three stages. An EXECUTION with no
   DECISION is work that bypassed the gate, and it fails.
3. **Coverage** — how much of the chain sits under a timestamp.
4. **Oversight** — was a held action approved by someone other than its actor.

There is a fifth check worth naming on its own: `decision.not_enforced` fails
when a recorded `deny` is followed by a successful execution. That is the
failure mode where the ledger looks strictest exactly where it is weakest —
every blocked action recorded, and none of them blocked.

## Verifiable by anyone

The point of stages 04 and 05 is that checking the evidence does not require
trusting the system that produced it.

```
pf provenance export /tmp/evidence
cd /tmp/evidence && python3 verify_provenance.py .
```

`verify_provenance.py` is stdlib-only, ~150 lines, and imports nothing from this
platform. Its spec is in its own docstring, so a verifier can be rewritten in any
language by someone who does not trust ours. The timestamp tokens are checked
with standard tools:

```
openssl ts -verify -digest <head-hash> -in anchors/<n>.tsr -CAfile <tsa-ca.pem>
ots verify anchors/<n>.head.ots
```

The canonical form a record hashes to is pinned: keys sorted, no whitespace,
UTF-8, no floats. Floats are refused at write time because `0.1` does not
round-trip identically in every language, and a digest a second implementation
cannot reproduce turns "verifiable by anyone" into "verifiable by us" without
anything failing.

## Anchoring

Two anchors, because they fail differently. RFC 3161 is immediate and legally
recognised, and its trust is the TSA's key — if that authority disappears with
its certificate, old tokens become unverifiable. OpenTimestamps needs no trusted
party at all and stays verifiable as long as Bitcoin does, but costs hours to
confirm. The RFC 3161 token answers "was this here this morning" today; the
Bitcoin attestation answers it in twenty years.

Anchoring is **not** in the hook. Both anchors need the network, and a PreToolUse
hook that makes a network call adds its latency and its failure modes to every
tool call the agent makes. The hot path only appends locally; anchoring runs
separately, from a scheduler or CI. Anchoring the head anchors everything under
it, so batching costs no coverage — the un-anchored window is the exposure, and
`pf provenance status` reports it rather than assuming it is zero.

Set `PF_TSA_URL` to your own authority. The default is freetsa.org, which is
free and public; an organisation with a qualified TSA should point at it, since
the evidentiary weight of a token is entirely the authority's. `PF_TSA_CA` is the
root certificate `--anchors` verification checks against.

## Fail-open or fail-closed

If the ledger cannot be written, does the action proceed?

```
PF_PROVENANCE_ENFORCE=0   (default) a recording failure never blocks work
PF_PROVENANCE_ENFORCE=1             an unrecordable action is a denied action
```

The default matches the existing hook, which deliberately does not block when
the platform is unimportable. A governance system whose failure mode is "the
whole team stops" gets switched off, and a switched-off system records nothing.
Regulated deployments should set `1` and accept the trade.

Two things ignore the flag and always fail closed, because a control a setting
can bypass is not a control:

- **Revocation.** A revoked actor is refused at INTENT, before the gate runs.
- **An unreadable `revoked.json`.** "I cannot tell whether you are revoked" must
  not resolve to "carry on".

## The ledger is not editable

`provenance/**` is on the gate's denylist. An agent that can edit the record of
what it did has no record of what it did — the hash chain makes tampering
*evident*, and the denylist makes it denied. The hooks write there directly
rather than through the Edit tool, so nothing legitimate is blocked.

The directory is gitignored (except the anchor tokens). It is append-only,
machine-written runtime state: every branch would conflict on it, and a merge
would silently reorder a hash chain into an invalid one. Durability comes from
anchoring the head and archiving `pf provenance export`, not from git.

## The second opinion: ASQAV

`vendor/asqav-compliance` is a GitHub Action that scans agent source for the
five controls it recognises — audit trail, policy enforcement, revocation, human
oversight, error handling — mapped to EU AI Act, DORA and ISO 42001. It runs on
every PR from `.github/workflows/ai-governance.yml`.

It is carried because it fails in the opposite direction to ours. `pf provenance
verify` is runtime evidence and says nothing about code no agent has exercised
yet; the scanner is static and says nothing about whether any of it ran. A clean
scan with a broken chain means the controls exist and do not work.

**It is reported, never enforced** (`fail-on-gaps: false`). The scanner is regex
over source: it scores a file that mentions `revoke` in a comment as having
revocation, and a correct implementation spelled differently as missing it. That
is not hypothetical here — it currently reports **Audit Trail: GAP** on
`pf/agents/base.py`, a file whose every LLM call writes three hash-linked ledger
records, because the patterns it looks for are `import asqav`, `.sign(`,
`audit_log` and `logger.`. Raising that score by renaming our functions to match
its regexes would change the score and not the governance, so we have not.

Useful as a prompt to go and look. Wrong as a merge gate — which is why
`pf provenance verify` is the one that blocks.

The action is pinned as a submodule and run from the checkout
(`uses: ./vendor/asqav-compliance`) rather than by tag, so the code that judges
our compliance cannot change without a commit here. Its licence is
**Elastic-2.0**, stricter than the platform's other upstreams: internal CI use is
well within scope, but exposing scanning as a tenant-facing feature is the
managed service the licence excludes. See `pf vendor licences`.

## The fourth side: a published control catalogue

The five stages above prove what an agent did. ASQAV asks whether the controls
exist in the source. Neither says **which controls there should be**, and for a
regulated deployment that is the part somebody external judges.

`vendor/ai-governance-framework` is the FINOS AI Governance Framework — 23 risks
and 23 controls, cross-walked to the EU AI Act, ISO/IEC 42001, NIST SP 800-53r5,
OWASP LLM/ML/ASI, FFIEC, SR 11-7, IOSCO and the UK and Canada regimes. Unlike the
other two upstreams it is machine-readable, so `pf.air` reads it rather than
citing it, and each `policy.yaml` entry now names the controls it discharges:

```yaml
    enforced_by: [pf.provenance.ledger:decision, platform/hooks/pre_tool_use.py]
    evidence: [pf provenance verify]
    controls: [AIR-DET-21, AIR-DET-4]
```

That single field is what lets the ledger described above answer a question it
could not answer before. `pf air crosswalk eu-ai-act` walks Article 12
(record-keeping) to `agent-decisions-are-recorded` and
`evidence-chain-is-tamper-evident`, and from there to the chain and the anchor —
so "how do you satisfy Article 12" is a path through this repository rather than
a paragraph about it.

Coverage is **derived on every run and never stored**, for the same reason the
onboarding ladder derives its verdicts: a recorded pass survives the change that
invalidated it. Only `fail` blocks a merge, and only for controls an entity
committed to in its own `air.yaml`. Everything else is reported — the platform
ships with eight controls it has not built and one that two policies claim while
naming enforcement that does not exist, and the report says so.

`docs/AIR.md` is the reference.
