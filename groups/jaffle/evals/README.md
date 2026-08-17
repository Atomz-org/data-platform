# Evals for jaffle

Prompts are code; these are their tests. Cases here cover what the sisters
**share and only share** — the group's ontology instance, its conformed
dimensions, its group-level metrics.

Three tiers run together, and each owns what only it can know:

| Tier | Lives in | Owns |
|---|---|---|
| platform | `platform/toolkits/<toolkit>/evals/` | health checks, and templates |
| **group** | **here** | what every sister in jaffle agrees on |
| project | `projects/<project>/evals/cases/` | one entity's business logic |

A case belongs here when it would be *wrong for a sister to disagree with it*.
If one sister could legitimately answer differently, it is a project case.

```json
{
  "name": "conformed_customer_grain_is_respected",
  "agent": "metric_gap_proposer",
  "why": "Why this case exists — what breaks without it.",
  "tags": ["conformed"],
  "input": {"gaps": ["..."], "mart_detail": "..."},
  "expect": {"proposals[].metric_type": {"any": {"equals": "ratio"}}}
}
```

    pf evals jaffle <project>          # contract tier + load every case
    pf evals jaffle <project> --live   # grade against the real models

Any change to an agent prompt must keep these green.
