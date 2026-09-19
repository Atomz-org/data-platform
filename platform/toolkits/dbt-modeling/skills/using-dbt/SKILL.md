---
name: using-dbt
description: Build, modify and debug dbt models. The default analytics-engineering skill.
---
<!-- Adapted from dbt-labs/dbt-agent-skills (vendor/dbt-agent-skills, Apache-2.0) — see registry.yaml. -->
# Using dbt

**Layer boundaries — enforced in review, and agents blur them constantly.**

| Layer | Owns | Never does |
|---|---|---|
| `staging` | **cleaning**, renaming, casting, dedupe — strictly 1:1 with a raw table | joins, aggregation, any grain change |
| `intermediate` | joins, reshaping | get exposed to BI or the semantic layer |
| `marts` | the grain and the physical table | define an aggregation *policy* |
| `semantic` | metric definitions and dimensions | store data |

## Staging: cleaning happens here, and only here

Staging is 1:1 with a raw table — one row in, one row out — and it is where **all**
cleaning lives. Nothing downstream re-cleans, because if two models both clean a
column they will eventually disagree.

**Do not hand-write staging models.** Run `pf gen-staging <group> <project>`: it
reads `contracts/annotations.yaml` and emits a model per resource, with cleaning
dispatched from each column's declared role.

| Role | Cleaning applied |
|---|---|
| `natural_key` / `foreign_key` | trim, blank → null (never lower-cased; keys are opaque) |
| `pii_email` | lower + trim — emails are case-insensitive, so joins and dedupe need it |
| `pii_name` / `pii_address` | trim, collapse internal whitespace, keep case |
| `status_enum` | lower + trim, so `accepted_values` stays stable |
| `currency_code` | upper + trim; not 3 chars → null (that is bad data, not a currency) |
| `geo_country` | upper + trim; not 2 chars → null |
| `money_amount` | `try_cast` to decimal(18,2); uncastable → null |
| `quantity` | `try_cast` to bigint; negative sentinels → null |
| `event_time` / `valid_from` / `valid_to` | `try_cast` to timestamp; pre-epoch → null |
| `free_text` | trim, empty → null |

Every model also gets `pf_dedupe(key)` — dlt merge can still land duplicates when
a source replays, and staging is the last place to fix that at 1:1 grain.

Column names come from the annotation's `rename` map. Declare it on the source,
not in SQL, so the warehouse name is decided once.

**What still does not belong in staging:** joins, aggregation, filters that drop
rows for business reasons, and derived columns. Those are intermediate or mart
concerns. Row-count in must equal row-count out, minus null keys and duplicates.

Conventions: `stg_<source>__<entity>`, `int_<domain>__<verb>`, `fct_`/`dim_` in marts.
Every model needs a `_models.yml` entry with a description and tests. Declare the
grain in `meta.grain` — the knowledge graph and the context card both read it.

A mart does **not** carry a `revenue` column. Revenue is a policy (which statuses,
which timestamp, which filters) and belongs in the semantic layer, defined once.

Before changing a column or a model, run `impact_analysis` and report the blast
radius including exposure owners.
