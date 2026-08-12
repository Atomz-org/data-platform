# Loop Constraints — data platform

> Binding. Read at the start of every loop run. Where a constraint can be
> enforced mechanically it is — see `gate.yaml`, the pre-commit hook and the
> PreToolUse hook. A constraint that relies only on the agent remembering it
> will eventually be skipped; that is not a hypothetical, it happened here.

## Scope
- One project per session. Never read another group or a sister project.
- Never edit `platform/**` from a project session — it is shared by every company.
- Cross-entity work happens only in the `<group>-rollup` project.

## Data changes
- Run impact analysis **before** changing a model, a column or a metric. Report
  the blast radius including exposure owners.
- Never `--full-refresh` or backfill from a loop. Those are plan-then-apply,
  human-gated.
- Never edit generated artefacts: `target/**`, `kg/graph.duckdb`,
  `kg/context_card.md`, `data/*.duckdb`.
- Staging is 1:1 with a raw table. Cleaning belongs there; joins and aggregation
  do not.

## Secrets
- Never ask for a credential in chat. Never read a secrets file.
- Use `secrets_view_redacted` and `secrets_update_fragment` only.

## Loop behaviour
- Max 3 attempts per finding. The count lives in `loop-ledger.json`, not memory,
  so a restart does not reset it. Escalate after; do not retry a fourth time.
- One fix per run. Never refactor unrelated code to make a fix land.
- Never disable a test to make a build green. A test that is wrong is a finding.
- Stop on budget depletion rather than degrading quality to fit.

## Communication
- Say what you are about to do before doing it.
- Report outcomes faithfully: if a build failed, show the output.
- Escalate ambiguity rather than guessing at business meaning.
