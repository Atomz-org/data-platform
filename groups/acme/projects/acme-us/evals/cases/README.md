# Evals for acme-us

Prompts are code; these are their tests.

## Two kinds of case live here

**`generated/`** — written by `pf evals-gen acme acme-us`. Each toolkit
ships eval *templates*: the shape of a correct judgement, with placeholders where
the table names go. Generation resolves those against this project's knowledge
graph, so the cases name **your** models and **your** columns.

Regenerating overwrites that directory and deletes anything whose template is
gone. Never hand-edit a file in it.

**Everything else in `evals/cases/`** — yours. Cases that encode acme-us's own
business rules, which no toolkit could have guessed. This is where the corpus
earns its keep: a restraint case naming the bridge tables that should get no
metric, a triage case for the settlement window only this entity has.

Nothing here is read by a sister, and nothing a sister writes is read here.

## Format

```json
{
  "name": "triage_recognises_our_late_settlement_window",
  "agent": "test_failure_triage",
  "why": "Why this case exists — what breaks in production without it.",
  "tags": ["triage"],
  "input": {"failures": [], "lineage": "..."},
  "expect": {"root_cause": "stale_source", "escalate": false}
}
```

`agent` is one of `test_failure_triage`, `freshness_triage`,
`metric_gap_proposer`. `why` is not decoration — without it a corpus decays into
assertions nobody dares change because nobody remembers whether they were
deliberate.

Keep prose matchers weak (`contains_any`, not exact strings). A case that pins
wording fails on a harmless rewrite, and a suite that cries wolf gets switched
off — which costs more than the case was ever worth.

## Commands

    pf evals-gen acme acme-us      # (re)ground the toolkit templates
    pf evals acme acme-us          # contract tier + load every case
    pf evals acme acme-us --live   # grade against the real models

`--samples N` runs each case N times. A case that passes 4 times in 5 is not
passing and not failing — it is an unstable prompt, which is the most useful
thing this suite can tell you before a prompt change ships.

Any change to an agent prompt must keep these green.
