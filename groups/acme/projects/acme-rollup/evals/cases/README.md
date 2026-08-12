# Evals for acme-rollup

Prompts are code; these are their tests. One JSON per case:

```json
{
  "name": "triage_recognises_stale_source",
  "input": {"failing_test": "...", "rows": "...", "model_sql": "..."},
  "expect": {"root_cause": "stale_source"}
}
```

Run with `pf evals acme acme-rollup`. Any change to an agent prompt must
keep these green.
