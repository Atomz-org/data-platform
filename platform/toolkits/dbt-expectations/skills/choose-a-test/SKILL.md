---
name: choose-a-test
description: Decide which kind of test an assumption belongs in.
---
# Which test

This platform has five ways to assert something, and picking the wrong one is
how a suite grows without getting safer. Choose by **what the assumption is
about**:

| The assumption is about | Use | Toolkit |
|---|---|---|
| A key, a reference, a fixed set of values | built-in `unique` / `not_null` / `relationships` / `accepted_values` | `dbt-testing` |
| The shape of a value — range, type, pattern | `dbt_expectations` | here |
| SQL logic given known inputs | unit test | `dbt-testing` |
| How the data moved compared to its own history | anomaly test | `dbt-elementary` |
| Whether a change altered results | `recce-review` diff | `recce-review` |

The ordering matters: **prefer the cheapest one that expresses the assumption.**
A built-in reads better in a diff than an expectation; an expectation is cheaper
to reason about than a unit test; a unit test is deterministic where an anomaly
test is statistical.

## The distinction people get wrong

**Static vs historical.** "Revenue is never negative" is static — an
expectation. "Revenue did not drop 60% overnight" is historical — Elementary.
Writing the second as a hardcoded threshold produces a test that is wrong within
a quarter and gets silenced rather than fixed.

**Data vs logic.** A test that fails when *the data* changes belongs in the
data tests. A test that fails when *the SQL* changes is a unit test. If you find
yourself loading real rows to prove a CASE ladder works, you wanted a unit test.

**Test vs contract.** "This column is always a non-null integer" is a contract
(`dbt-govern`), enforced at build. A test that re-asserts a contracted column is
checking the warehouse's own enforcement.

## Before adding any of them

Run `impact_analysis` on the model. It tells you how many things depend on the
column you are about to assert — which is the honest measure of whether the test
is worth its runtime, and which consumers to name if it ever fails.

And a test that always warns and is never fixed is noise. Delete it, or promote
it to something that blocks.
