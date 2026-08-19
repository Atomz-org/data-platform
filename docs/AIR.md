# AI risk and controls

The fourth side of this platform's governance question, and the only one that can
be read by code.

| side | what it answers | where |
|---|---|---|
| runtime evidence | what an agent actually did | `pf.provenance`, `docs/GOVERNANCE.md` |
| static analysis | whether a control exists in the source | `vendor/asqav-compliance` |
| artefact templates | what a regulator is handed | `vendor/public-sector-ai-playbook` |
| **risk taxonomy and control catalogue** | **which controls there are, and which regulation each discharges** | **`pf.air`, this document** |

Before this, `policy.yaml` held ten rules somebody wrote down. They were enforced
and they were evidenced, but they had no external referent — so "does this
satisfy the EU AI Act?" had no answer even though every fact needed to answer it
was already on disk. The catalogue is that referent.

## Catalogues are registered, not hardcoded

`pf.air` reads **control catalogues**. FINOS is the one this repository pins; it
is not the one the code knows about. Where a corpus lives, what its frontmatter
keys are called, what its type codes mean and how its ids are formed are all
declared on a `CatalogueSource` in
[platform/src/pf/air/sources.py](../platform/src/pf/air/sources.py). Nothing in
the parser, the coverage derivation, the register, the gate or the CLI names a
framework.

Adding one is a `CatalogueSource` — in this repo, or on the `pf.catalogues`
entry point of any installed distribution, the same seam and the same reasoning
as `pf.tools`:

```toml
[project.entry-points."pf.catalogues"]
acme-controls = "acme_controls:CATALOGUE"
```

That matters here specifically because the platform is multi-tenant. A
financial-services framework is the right default for some sisters and noise for
others, and swapping it must not be a fork of the reader. Prefixes must be unique
across enabled catalogues — two claiming `AIR-` would make an `air.yaml` baseline
ambiguous — so `discover()` refuses the collision loudly rather than resolving it
quietly.

`pf air catalogues` lists what is registered and which corpora are on disk.

## What is pinned today

[`vendor/ai-governance-framework`](../vendor/ai-governance-framework) — the FINOS
AI Governance Framework, CC BY 4.0, pinned as a submodule like every other
upstream. It is documentation only: no code of theirs runs here.

- **23 risks**, typed `RC` (regulatory), `OP` (operational), `SEC` (security)
- **23 controls**, typed `PREV` (preventative) or `DET` (detective)
- **13 regulatory crosswalks** — EU AI Act, ISO/IEC 42001, NIST SP 800-53r5,
  NIST AI 600-1, OWASP LLM/ML/ASI, FFIEC, SR 11-7, IOSCO, UK and Canada regimes,
  and the agentic threat registry

Risks 24–29 are the agentic ones — authorization bypass, tool-chain
manipulation, MCP supply-chain compromise, state poisoning, multi-agent trust
boundaries, credential harvesting. That is this platform's actual threat surface,
and it is why this framework rather than a generic one.

### Ids are derived, not stored

A control's public id is its source's `id_template` rendered against that
source's prefix and the document's own frontmatter — for FINOS,
`AIR-{type}-{sequence}`.
`docs/_mitigations/mi-21_agent-decision-audit-and-explainability.md` with
`type: DET` and `sequence: 21` is **`AIR-DET-21`**.

The consequence matters: **a `type:` change upstream renames a control**, and
every `air.yaml` baseline naming the old id silently stops matching. That is why
the pin is `kind: data` in `registry.yaml` (severity `error`) and why
`pf air verify` runs inside `pf vendor verify`.

Sequence numbers are sparse — 1, 2, 4–10, 14, 16–20, 22–29 — because entries have
been retired. Nothing may assume a dense range.

## How a control becomes ours

A control is discharged by a **policy** — an entry in
[`platform/src/pf/ontology/policy.yaml`](../platform/src/pf/ontology/policy.yaml)
listing that control in its `controls:` field. Nothing new was invented for this:
`policy.yaml` was already `intent → constraint → enforced_by → evidence`, and the
framework supplies the missing fifth column.

```yaml
  - id: agent-decisions-are-recorded
    intent: >
      Every tool call an agent makes is written down before it happens and after
      it happens, and the gate's verdict is recorded for allows as well as denies.
    applies_to: {artifact_glob: "**"}
    constraint: action_recorded
    severity: error
    enforced_by: [pf.provenance.ledger:decision, platform/hooks/pre_tool_use.py]
    evidence: [pf provenance verify]
    controls: [AIR-DET-21, AIR-DET-4]     # <- the mapping
```

Many-to-many on purpose. One control needs several rules (`AIR-DET-21` is
answered by the recorded decision *and* by the chain that makes the record
tamper-evident); one rule discharges several controls.

## Coverage is derived, never recorded

`pf air coverage` recomputes every verdict from the repository on each run. Nothing
is stored, because a recorded pass survives the change that invalidated it — the
same rule `pf.onboard.ladder` states for the onboarding ladder, using the same
vocabulary (`pf.checks`).

| verdict | means |
|---|---|
| `fail` | no policy claims the control, **or** every claiming policy has an empty `enforced_by`, **or** the artefact it names does not resolve |
| `unexercised` | the artefact resolves, but the evidence it declares has produced nothing |
| `pass` | the artefact resolves and its evidence exists |

**Only `fail` closes a gate.** `unexercised` is reported loudly and exits zero:
walling a project off because a ledger has not been written yet is how a gate
stops being run at all.

"Does the artefact resolve" is a real question, not a formality. `enforced_by`
naming `pf.provenance.ledger:decision` is checked by importing it; `gate.yaml:denylist`
by reading the file and looking for the section; `pf.ontology.validate:money-without-currency`
— a *rule id*, hyphenated and therefore never a Python symbol — by finding the
literal in the module source. Rename the function and the control goes red at the
next run, rather than at the next audit.

## Declaring a baseline

`air.yaml` is hand-written and carries the judgement. Group over project,
deep-merged, the same two-level pattern as `tools.yaml`:

```
groups/<group>/air.yaml                       the family's baseline
groups/<group>/projects/<project>/air.yaml    this entity's refinement
```

Both are **scaffolded, never hand-created**: `pf new-group` writes the group's,
the `air` capability writes each project's, and `pf bootstrap` backfills both for
anything that predates this layer. A new group or project therefore arrives with
a declaration already in place and a gate already wired.

```yaml
version: 1
profile:
  ai_type: Agentic_AI
  architecture_pattern: Agentic/Autonomous_AI
baseline:
  - AIR-PREV-18   # these block the merge
  - AIR-DET-21
accepted:
  - control: AIR-PREV-14
    reason: >
      No production warehouse yet; encryption at rest is the warehouse's job.
    owner: someone@example.com
    review_by: 2027-01-01
```

- **`baseline:` unions, it does not replace.** A project may commit to more than
  its family, never to less. A baseline you can opt out of by editing your own
  file is not a baseline.
- **`accepted:` requires `reason` *and* `owner`.** An acceptance without a reason
  is a gap with better formatting; one without an owner is a decision nobody can
  be asked about. `pf air` refuses to load a declaration missing either.
- A control cannot be both committed to and accepted. `validate()` says so.

**A scaffolded baseline is empty, on purpose.** A scaffolder that pre-commits an
entity to a set of controls produces commitments nobody made, and the first gate
run fails on a decision never taken.

`pf air baseline <group> [project] --suggest` proposes the controls that already
pass and are not yet declared, ready to paste — a ratchet against regression
rather than a wall of work. It deliberately does not write the file: committing
to a control is a decision with an owner.

## Why the register is generated

`groups/<g>/projects/<p>/governance/air-register.md` is derived from `air.yaml`
plus a fresh coverage run, and is on the gate denylist. Hand-editing it would make
it disagree with the declaration it came from, and the next `pf air register`
discards the edit — the same argument that denies every other generated artefact
here. Change `air.yaml`, then regenerate.

It carries the credit line of **every catalogue it actually drew from**, collected
from the loaded sources rather than templated. So a catalogue swapped out takes
its obligation with it, one added brings its own, and a catalogue that requires no
credit still gets its origin stated — a governance artefact with no provenance is
one nobody can check. The obligation travels with the derived artefact, not with
the repository, and this is the artefact a regulator is handed.

## Commands

| command | answers |
|---|---|
| `pf air catalogues` | which catalogues are registered, and which are checked out |
| `pf air risks [--type SEC]` | which risks exist, and what claims to mitigate each |
| `pf air controls [--type PREV] [--risk AIR-SEC-24]` | which controls exist |
| `pf air show AIR-DET-21` | one document, its links, and every regulation it cites |
| `pf air coverage [group project]` | which controls we discharge, with evidence |
| `pf air gaps` | only the failures, most-cited regime first |
| `pf air crosswalk eu-ai-act` | the regulator's view: each article, and which of our policies discharges it |
| `pf air baseline <g> [p] [--suggest]` | what this entity committed to, or what it could |
| `pf air register <g> <p>` | regenerate the register |
| `pf air gate <g> <p>` | **exit non-zero** when a committed control is failing |
| `pf air verify` | the vendored corpus against its own contract |

`pf semantic otop` also changed: every constraint in the exported manifest now
carries the controls it discharges and their resolved citations, so the otop
export is legible to an assessor who has never heard of `pii-not-in-consumption`
but knows what EU AI Act Article 10 is.

## Where it runs

`.github/workflows/ai-governance.yml`, job `air-baseline`, alongside `provenance`
(blocking) and `compliance-scan` (reporting). It checks out submodules — the other
jobs do not need to and this one cannot work without it — verifies the corpus,
writes coverage into the job summary, and gates each entity on its own baseline.

## Known state

No group commits to anything yet — every scaffolded `baseline:` is empty, so
`pf air gate` passes everywhere and blocks nothing. That is the correct starting
point, not an oversight: run `pf air baseline <group> --suggest` and commit to
what you mean to hold.

The platform ships with controls it has not built, and says so rather than
mapping a policy that names nothing:

`AIR-PREV-2` external-KB filtering · `AIR-PREV-3` user/app/model firewalling ·
`AIR-PREV-8` QoS and DDoS · `AIR-DET-9` denial-of-wallet spend monitoring
(partial — `loop-budget.md` exists, nothing alerts) · `AIR-PREV-14` encryption at
rest · `AIR-DET-15` LLM-as-a-judge (partial — `pf.evals`) · `AIR-PREV-17` AI
firewall · `AIR-PREV-20` MCP server security governance.

`AIR-DET-13` fails for a different and more interesting reason: two policies
claim it, and both name enforcement that does not exist —
`pf.kg.build:model-grain` and `pf.ontology.validate:metric-shaped-column`. Those
were paper controls before this catalogue arrived; it is what found them.

The vendored corpus also has a defect of its own. Seven risk documents have a
list comment running into the next key with no newline, so YAML absorbs
`related_risks:` into the previous citation list — those documents have lost
their related-risk links upstream, and gain citations into a regulation that
never mentioned them. `pf air verify` diagnoses it precisely and warns rather
than fails: it is a one-newline fix in someone else's repository, and our merge
gate should not be hostage to their typo.

## Attribution

The framework is © FINOS, licensed
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Upstream is
[finos/ai-governance-framework](https://github.com/finos/ai-governance-framework);
we pin a fork so a FINOS change lands as a reviewed merge rather than a branch
that moved under us. Changing back is one `url` line in `.gitmodules` — nothing in
`pf.air` knows which remote it came from.
