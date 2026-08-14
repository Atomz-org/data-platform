---
when: Adding data tests or unit tests to a model.
rules:
  - Unit-test non-trivial SQL — window functions, CASE ladders, incremental predicates.
  - A test encodes an assumption; when the assumption changes, change the test rather than the data.
---

# dbt-testing

Data tests check the rows that arrived; unit tests check the logic that produced
them. They fail for different reasons and a passing suite of one says nothing
about the other.
