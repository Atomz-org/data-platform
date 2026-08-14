---
when: Building, modifying or debugging a dbt model. The default analytics-engineering toolkit.
rules:
  - Run impact_analysis before any schema or model change and report the blast radius, including exposure owners.
  - Confirm a model change empirically with recce-review afterwards — lineage says what could break, only a diff says what did.
---

# dbt-modeling

Structure questions ("where does this come from", "what breaks if I change it")
are answered from the knowledge graph, not by grepping the repository. The graph
knows about exposures and downstream owners; grep does not, which is how a change
ships without the people it breaks ever hearing about it.
