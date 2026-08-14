---
when: Any question about a business quantity — revenue, churn, retention, counts.
rules:
  - Never answer a metric question with ad-hoc SQL; if no metric fits, say which definition is missing.
  - The mart declares the grain; the metric declares the aggregation policy.
  - Prefer composing metrics (ratio, derived) over recomputing an existing one.
---

# dbt-semantic

The semantic layer is the only governed answer to a business question. Raw SQL
that recomputes a defined metric is a bug, not a shortcut — it is how one company
ends up with two revenues that disagree and no way to tell which is right.

When a question has no metric behind it, the useful answer is naming the missing
definition. Silently falling back to SQL produces a number that looks official,
came from nowhere, and will be quoted back later.
