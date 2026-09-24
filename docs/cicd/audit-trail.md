# The audit trail — what replaces a hand-written `.compliance-trace/`

**Written for:** anyone asking "how do we know what the agent actually did?"

## The thing being replaced

A common pattern in AI-assisted repositories is a folder of hand-written trace
records — a reviewed reference implementation uses `.compliance-trace/`, with
one Markdown file per task in six prose sections: *Intention · Planning ·
Execution · Results · Traces · Output*.

It is a good idea with a structural problem: **it is prose, written by the
thing it describes, after the fact.** Its own records concede the consequence —
authorship on those files is self-reported in the text, with no git,
cryptographic or CI anchor behind it. Nothing forces a record to exist, nothing
checks one is true, and nothing prevents editing one later.

That folder held **one record**.

## What this repo does instead

Not a folder someone remembers to fill in. A chain something else writes while
the work happens.

```
provenance/chain.jsonl     19,534 entries
provenance/head.json       {"seq": 19500, "hash": "8e3223d9ecc2…"}
```

Every agent action is **three records**, written at different moments:

| Stage | When | Written by |
|---|---|---|
| **INTENT** | before the tool runs | `platform/hooks/pre_tool_use.py` |
| **DECISION** | after the gate is consulted, still before the tool runs | same hook |
| **EXECUTION** | after the tool returns | `platform/hooks/post_tool_use.py` |

One real entry, abbreviated:

```json
{"seq": 19531, "stage": "execution", "actor": "sswaminathan",
 "tool": "Bash", "target": "grep -n \"_vendor_docs\" platform/src/pf/…",
 "ts": "2026-09-24T16:38:42Z",
 "hash": "1f1cdfbef6e2f170…", "prev": "a7afc0b8d9792802…"}
```

`prev` is the previous record's hash. Change any earlier record and every hash
after it stops matching.

## The four differences that matter

**1. Nobody writes it.** A hook does, on every tool call. There is no step to
forget and no judgement about whether this action was worth recording.

**2. The order is the argument.** INTENT is written **before** the gate is
consulted, so a *denied* action still leaves evidence it was attempted. The
hook's own docstring states why:

> *"A gate that only logs its refusals can prove it said no; it cannot prove it
> was ever asked."*

**3. Editing it is detectable.** Each record hashes the one before.

**4. Agents cannot touch it.** `provenance/**` is denied to every agent in
`gate.yaml` — you may not edit the record of what you did.

## What CI actually verifies — and what it does not

This is the part to read carefully, because the honest answer is narrower than
it first looks.

The `Provenance chain` job runs on every pull request and **does** block:

```bash
uv run pytest platform/tests/gate/test_provenance.py -q
```

That proves the **tamper detection still works** — that a doctored chain is
still caught, an ungated execution is still a finding, a self-approval is still
refused.

But the two steps that verify the **actual ledger**:

```bash
if [ -f provenance/chain.jsonl ]; then uv run pf provenance verify --anchors; fi
if [ -f provenance/chain.jsonl ]; then python3 platform/entrypoints/verify_provenance.py provenance; fi
```

…are wrapped in a guard that is **always false in CI**. `provenance/*` is
gitignored (`.gitignore:179`), so `git ls-files provenance` returns **0** and a
fresh checkout has no chain in it.

**This is declared, not hidden.** The workflow says so in the step itself:

> *"Skipped rather than failed when the runner has no ledger — CI checks out
> source, and a fresh checkout has no runtime evidence in it, which is not the
> same as evidence that failed."*

That reasoning is sound. The ledger is runtime evidence; verification runs
where the records are written. **The residual is still real:** CI proves the
verifier works, it does not prove your ledger is intact. That check has to
happen on the machine that holds the chain.

## Two gaps worth closing

Both verified against the repository as it stands.

**1. `CLAUDE.md` overstates it.** Lines 31-32 say:

> *"`pf provenance verify` blocks CI"*

On a pull request it never runs — the guard above is false. The *job* can block
(its unit tests can fail), but the sentence reads as though your ledger is
verified on every PR, and it is not. This is the same doc-versus-code drift the
generate-and-compare checks exist to prevent, in a file that is not generated.

**2. Nothing has ever been anchored.** `.gitignore:180` carves out
`!/provenance/anchors/` and the `Timestamp anchor coverage` job's comment says:

> *"The anchor tokens are the one thing under `provenance/` that is committed,
> precisely so an auditor gets them alongside the chain."*

But `provenance/anchors/` **does not exist** and has zero committed files. The
hash chain proves *internal* consistency — that records were not altered
relative to each other. An RFC 3161 or OpenTimestamps anchor is what proves the
chain existed *at a point in time*, which is what stops the whole chain being
regenerated wholesale. Without a committed anchor that property is designed but
not yet in force. `docs/GOVERNANCE.md` §"Scheduling the anchor" covers how.

The check is green because it is `if: github.event_name != 'pull_request'` and
never blocking — deliberately, so an author is not blocked by something they
cannot fix. Green here means "not asked", not "verified".

## The honest summary

| | `.compliance-trace/` | this repo |
|---|---|---|
| Records | 1, hand-written | 19,534, hook-written |
| Coverage | what someone chose to write up | every tool call |
| Authorship | asserted in prose | git identity + actor on each record |
| Tamper-evident | no | yes, SHA-256 chained |
| Verified in CI | no | the *verifier* is; the *ledger* is not |
| Anchored in time | no | designed, **not yet in force** |

Strictly better on every row — and still not finished on the last two. Saying
so is the point: an audit trail whose limits are documented is worth more than
one whose limits are discovered.

## Commands

```bash
uv run pf provenance verify --anchors   # verify the local ledger
uv run pf provenance log                # read it
uv run pf provenance export             # archive evidence for an auditor
uv run pf provenance anchor             # put the head hash beyond this repo
```
