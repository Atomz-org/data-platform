---
name: add-expectations
description: Add dbt_expectations tests for distributions, types, ranges and row counts.
---
# Expectations

`dbt_expectations` is the Great Expectations vocabulary as dbt tests. Reach for
it when the assertion is about a **value's shape** — a range, a type, a
distribution — which the built-in four cannot express.

```yaml
# transform/packages.yml
- package: metaplane/dbt_expectations
  version: [">=0.10.0", "<0.11.0"]
```

## Generate from the role, not from imagination

Annotations already declare intent, and the role determines the expectation:

| Role | Expectation |
|---|---|
| `money_amount` | `expect_column_values_to_be_between` with `min_value: 0` |
| `percentage` | `expect_column_values_to_be_between` 0–1 (or 0–100 — pick once, per project) |
| `event_time` | `expect_column_values_to_be_between` bounded by `current_timestamp` — catches the year-2107 row |
| `status_enum` | built-in `accepted_values`, **not** an expectation |
| `natural_key` | built-in `unique` + `not_null`, **not** an expectation |
| `email` / `url` | `expect_column_values_to_match_regex` |
| any numeric | `expect_column_values_to_be_of_type` where the warehouse is loose about it |

Whole-model shape is worth one test each:

- `expect_table_row_count_to_be_between` — a floor, so an empty build fails loudly
- `expect_table_column_count_to_equal` — on a contracted model only; elsewhere it
  fights every legitimate column addition

## Rules

**Do not restate a built-in.** `unique`, `not_null`, `accepted_values` and
`relationships` ship with dbt and read better in a diff. An expectation that
duplicates one is a second thing to update when the assumption changes.

**Severity: `error` for anything that would corrupt a metric** — a negative
`money_amount`, a null key. `warn` for distribution drift, which is a question,
not a defect.

**Bound the range in a variable, not a literal.** A threshold hardcoded in three
models is three places to edit and two that get missed. Put it in
`dbt_project.yml` `vars:` and reference it.

**One assumption per test.** A test asserting a range *and* a type fails without
saying which half broke.

## Where this stops

An expectation tests a column. It cannot test business logic — that is a unit
test (`dbt-testing`), because logic needs fixed inputs and an expected output.
And it cannot tell you a number is *wrong*, only that it is oddly shaped; a
wrong number that looks normal is what the semantic layer and `recce-review`
are for.
