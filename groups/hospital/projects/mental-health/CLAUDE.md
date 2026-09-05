# mental-health — project context

@kg/context_card.md

Group: `hospital`. The sister roster lives in the group card above —
do not read a sister's files from here.

## Business rules the graph cannot encode
<!-- Domain facts an agent cannot derive from the models. Keep it tight. -->
- Registry NULL values are suppressed/not-applicable cells — never zero-fill,
  never coalesce. A published 0 is a real zero; NULL is absence of publication.
- Survey respondents are anonymous members of the public, NOT Patients.
  Never join survey data to patient-grain facts.
- Patient-level and population-level data meet only in
  `fct_diagnosis_benchmark`, only as shares at conformed ICD-10 group grain.
- Screening and ECG cohorts have no event time upstream — they carry no time
  axis and stay out of the semantic layer by design.
- The diagnosis vocabulary bridge is `transform/seeds/diagnosis_map.csv`;
  changing a mapping changes the benchmark — `pf impact` first.
  Design rationale and research anchors: `decisions/ADR-0001`.

## The semantic stack
Vocabulary is platform-wide and already loaded in this project's graph before any
data exists — `kg_search` finds concepts, relations and policies on day one.

| Ask | Command |
|---|---|
| What relates to what | `pf semantic topology` |
| What must hold, and what enforces it | `pf semantic policy` |
| BI / WrenAI projection | `pf semantic mdl hospital mental-health` → `mdl/mdl.json` |
| Re-run every generated artefact | `pf bootstrap hospital mental-health` |

A foreign key must be declared with `links={"col": "SomeClass"}`, and the topology
must already relate the two classes — that binding is what makes join conditions
derivable rather than guessed. `pf check` fails on an undeclared join.

## Conventions
- Every dlt resource is annotated (`@annotate`) before any model is written.
- Marts declare `meta.grain`; the semantic layer owns aggregation policy.
- Ask the graph before reading files: `kg_search`, `kg_neighbors`, `kg_path`.
- Run `impact_analysis` before changing a column, a model or a metric.
