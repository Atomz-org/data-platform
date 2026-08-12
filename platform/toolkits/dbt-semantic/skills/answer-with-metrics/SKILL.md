---
name: answer-with-metrics
description: Answer a natural-language business question from the semantic layer. Use for ANY question about a business quantity.
---
# Answering with metrics

dbt Cloud's Semantic Layer API does not exist here. The equivalent is the
MetricFlow CLI, wrapped as `query_metrics`.

1. `list_metrics` — see what is defined.
2. `get_dimensions` — see how it can be sliced.
3. `query_metrics(metrics=[...], group_by=[...], where=...)`.

**If no metric covers the question**, say so explicitly and name the missing
definition. That gap report is the input to a PR adding the metric — it is how
the semantic layer grows from real questions instead of upfront guessing.

Do not answer a metric question with `execute_sql_query`. Recomputing a defined
metric in ad-hoc SQL is how one company ends up with four different revenues.

Always state which metric you used and its filter, so the number is auditable.
