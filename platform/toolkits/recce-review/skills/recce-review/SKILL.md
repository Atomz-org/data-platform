---
name: recce-review
description: >
  Review what a dbt change actually did to the data, using Recce. Triggers when:
  reviewing a model change before commit, checking whether numbers moved, "did
  this change break anything", or after `impact_analysis` reports a blast radius
  that needs confirming.
---
# Reviewing a dbt change with Recce

Ported from `vendor/recce/claude-plugin/plugins/recce/skills/recce-review`, cut
down to the local workflow. The upstream skill is mostly Recce Cloud session
handoff; this platform declined cloud mode (state would leave the machine — see
the `recce` entry in the vendor registry), so none of that applies here.

## Where this sits

`impact_analysis` and this skill answer different questions and you usually need
both:

| | question | source |
|---|---|---|
| `impact_analysis` | what *could* break | the knowledge graph, before running |
| Recce | what *did* change | two dbt builds, after running |

Structural blast radius does not predict arithmetic. A refactor with a huge
downstream fan-out can move nothing; a one-line `case` change with two dependents
can move revenue four percent. **Report both or you have not reviewed the change.**

## Procedure

1. **Run the structural check first.** `impact_analysis` on the changed model.
   If it reports `breaking`, say so up front — the diff is confirmation, not a
   second opinion that can overturn it.

2. **Confirm there is a baseline.**
   ```bash
   pf tool doctor <group> <project>
   ```
   No baseline means there is nothing to diff against. Capture one from a build
   that was green *before* the change:
   ```bash
   pf tool recce baseline <group> <project>
   ```
   Never capture a baseline from the build that contains the change. That
   compares the change to itself and always reports "no differences", which is
   the single most common way this tool gets misread.

3. **Build, then diff.**
   ```bash
   pf seed <group> <project>
   pf tool recce run <group> <project>
   ```

4. **Read the diff.** The checks in `transform/recce.yml` are derived, never
   written by hand:

   ```
   contracts/annotations.yaml   column -> ontology role
   ontology concepts.yaml       role   -> review intent (+ pii flag)
   pf.tools.recce               intent -> recce check type
   ```

   | intent | comes from | becomes |
   |---|---|---|
   | `identity` | `natural_key`, `surrogate_key` | the key a value diff aligns rows on |
   | `distribution` | any `decimal`/`integer` role | profile diff — "revenue moved four percent" |
   | `categories` | `status_enum`, `geo_country`, `currency_code` | keyed group-by — a value gained or lost |
   | `none` | anything `pii: true`, and free text | excluded from every value-level check |

   **A missing check is a missing role.** If a column you care about is not
   covered, the fix is `meta: {role: ...}` on that column, then
   `pf tool recce config` — not an edit to `recce.yml`. Coverage is a direct
   function of how well the marts are annotated.

5. **Classify every difference before reporting.** A diff is not a verdict.
   - *intended* — the change was meant to do this; say which requirement.
   - *collateral* — a real change nobody asked for. This is the finding.
   - *noise* — non-deterministic ordering, a timestamp, a re-run artefact.

   **A difference you cannot place in one of those three is a finding, not
   noise.** Say you could not explain it. An unexplained diff reported as "looks
   fine" is worse than not running the review.

6. **Report.** Blast radius from the graph, what moved from the diff, and the
   exposure owners for anything downstream that changed. `transform/recce_summary.md`
   is written by step 3 — quote it rather than paraphrasing numbers.

## Reading the UI

```bash
pf tool recce serve <group> <project>     # Recce's own UI, :8000
pf ui                                     # control plane → Review tab
```

The Review tab embeds the same server beside this platform's lineage and impact.
In Dagster the review is the `recce_review` asset, downstream of the marts, with
the summary and a deep link attached to the run.

## Rules

- **Never edit `transform/recce.yml` by hand.** It is generated from
  `contracts/annotations.yaml`. Wanting a different check means a role is wrong
  or missing; fix the annotation and run `pf tool recce config`.
- **Never edit `recce_state.json` or `target-base/`.** Both are gate-denied.
  Editing a recorded diff makes the review lie about what happened.
- **Never pass `--cloud`.** Declined at the platform level.
- **Never add a check over a PII column.** A value-level diff writes the compared
  rows into `recce_state.json`, which is durable and shared. The generator
  excludes them by role and the `review-artifacts-exclude-pii` policy says why;
  hand-adding one puts real addresses in a committed artefact.
- A failing check is a *finding*, not a failed command. `pf tool recce run`
  exits zero on differences by design; use `--strict` only in CI, where the
  point is to block.
