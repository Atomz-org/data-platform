# Recce — dbt review for globex/globex-core

`pf impact` says what *could* break. Recce says what *did* change.

## The loop

```bash
pf seed globex globex-core                 # build green
pf tool recce baseline globex globex-core  # capture that build as the baseline
#   ... change a model ...
pf seed globex globex-core
pf tool recce run globex globex-core       # diff against the baseline
pf tool recce serve globex globex-core     # read it in the Recce UI
```

## What is generated

`transform/recce.yml` is derived from `contracts/annotations.yaml` — a
`natural_key` role becomes a value-diff primary key, a `money_amount` becomes a
profile diff. **Edit the roles, not the config**; `pf bootstrap` regenerates it.

`transform/recce_state.json` and `transform/target-base/` are build artefacts.
Both are gate-denied for the same reason `target/` is: hand-editing a recorded
diff makes the review lie.

## Where the artefacts live

Not in git — in the artefact store (`docs/ARTIFACTS.md`). The baseline is
published under the ref it was built from and pulled by anything diffing
against that ref; the recorded review is published under the branch under
review. The commands above do both without being asked.

```bash
pf artifacts status                          # is a store configured, and reachable
pf artifacts pull globex globex-core      # baseline + review onto this machine
pf artifacts ls globex globex-core        # what has been published
```

With no store configured everything stays local, which is the right behaviour
on a laptop that built its own baseline ten seconds ago. In CI it is not: a
runner has code and no warehouse, so an unconfigured store there means the
review reports *not exercised* rather than green. Set the two secrets named in
`docs/ARTIFACTS.md`.

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
