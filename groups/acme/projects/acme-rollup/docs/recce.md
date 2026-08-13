# Recce — dbt review for acme/acme-rollup

`pf impact` says what *could* break. Recce says what *did* change.

## The loop

```bash
pf seed acme acme-rollup                 # build green
pf tool recce baseline acme acme-rollup  # capture that build as the baseline
#   ... change a model ...
pf seed acme acme-rollup
pf tool recce run acme acme-rollup       # diff against the baseline
pf tool recce serve acme acme-rollup     # read it in the Recce UI
```

## What is generated

`transform/recce.yml` is derived from `contracts/annotations.yaml` — a
`natural_key` role becomes a value-diff primary key, a `money_amount` becomes a
profile diff. **Edit the roles, not the config**; `pf bootstrap` regenerates it.

`transform/recce_state.json` and `transform/target-base/` are build artefacts.
Both are gate-denied for the same reason `target/` is: hand-editing a recorded
diff makes the review lie.

## In Dagster

The `recce_review` asset runs downstream of this project's marts and attaches the
diff summary plus a link to the Recce UI to the run. Dagster OSS has no
custom-tab extension point, so the single-pane view lives in `pf ui` →
**Review**, which embeds Recce beside the lineage this platform already tracks.

## Read it against the semantic layer

`pf ui` → **Workspace** joins this review to the MDL manifest on the model, so a
recorded diff is read as *which published entity moved and what it carries*
rather than as a list of dbt node names. It needs the `wren` tool on as well;
both are on by default for a new group.
