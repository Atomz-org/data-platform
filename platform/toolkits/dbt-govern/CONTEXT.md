---
when: A dbt run or test failed, or a model needs a contract, access modifier or version.
rules:
  - Classify a failure before fixing it — upstream_data, model_logic, stale_source or test_too_strict.
  - Re-running is only correct for stale_source; the other three need a real change.
  - A test that fails because the test is wrong is a real outcome — say so rather than contorting the model.
---

# dbt-govern

The four root-cause classes are not labels, they are four different responses.
Getting the class wrong sends an engineer down the wrong path, which costs far
more than the triage saved.

The failure mode worth naming: making a test green by filtering out the rows that
fail it. That destroys data and reports success, and it is what an agent under
pressure to close a red build will reach for.
