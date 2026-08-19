# dbt-expectations — zenith/zenith-de

Great Expectations' vocabulary as native dbt tests, installed project-wide.
Use any of it in a model's yml:

```yaml
models:
  - name: fct_payments
    columns:
      - name: amount
        data_tests:
          - dbt_expectations.expect_column_values_to_be_between:
              min_value: 0
              row_condition: "status = 'captured'"
```

## The generated floor

`transform/tests/expectations/` holds tests derived from the ontology — the
same chain that generates recce checks:

    annotations.yaml   column -> role
    knowledge graph    role + pii, resolved per mart column
    this tool          what the role asserts -> a dbt-expectations test

An annotated mart must not be empty; its declared identity must be unique and
never null. That is all — anything sharper is a judgement about one table, so
it belongs in that model's yml (above), not in a generator.

**Edit the roles, not the generated files.** `pf bootstrap` (or
`pf tool expectations config zenith zenith-de`) regenerates them.

## Running

They are ordinary dbt tests: `pf seed`, `dbt build` and the Dagster assets run
them; `pf tool expectations run zenith zenith-de` runs just the generated
floor (`tag:expectations`). Results land in Elementary's history with every
other test.
