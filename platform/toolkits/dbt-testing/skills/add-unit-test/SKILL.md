---
name: add-unit-test
description: Add a dbt unit test for model logic. Use for non-trivial SQL — window functions, CASE ladders, incremental predicates.
---
# Unit tests (dbt Core >= 1.8)

Data tests check the output of a real run. Unit tests check the *logic* against
fixed inputs, so they catch a broken CASE branch that current data never hits.

```yaml
unit_tests:
  - name: test_revenue_excludes_refunded
    model: fct_revenue
    given:
      - input: ref('stg_stripe__charges')
        rows:
          - {id: 1, status: 'succeeded', amount: 100, currency: 'USD'}
          - {id: 2, status: 'refunded',  amount: 50,  currency: 'USD'}
    expect:
      rows: [{total_revenue: 100}]
```

Write one for every model whose logic encodes a business rule. Test-drive it:
write the failing unit test first, then the SQL.
