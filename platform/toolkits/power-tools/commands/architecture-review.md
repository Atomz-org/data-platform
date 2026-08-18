---
name: architecture-review
description: Check the active project against the platform's architecture — ontology conformance, declared joins, grain, layering and the semantic contract.
disable-model-invocation: "yes"
---

# Architecture review

In this platform "architecture" is not a diagram, it is a set of claims the graph
can check. Review = find the claims that are no longer true.

Scope: `$ARGUMENTS` (a subtree, a layer, a concept), else the whole project.

## 1. Conformance, mechanically

```bash
uv run pf check                     # ontology conformance + blast radius of your changes
uv run pf semantic topology         # the named relations between classes
uv run pf semantic policy           # intent → constraint → artifact → evidence
```

`validate_annotations` (MCP) for the source layer. `pf check` fails on an
undeclared join — that failure is the single highest-value signal here, because a
join that is not declared is a join whose condition was *guessed*.

## 2. The four claims worth checking by hand

1. **Every dlt resource is annotated before any model exists.** A model built on
   an unannotated resource has no concept behind its columns; the semantic layer
   downstream is then decoration. `ontology_classes` + `validate_annotations`.
2. **Every foreign key is declared** as `links={"col": "SomeClass"}` *and* the
   topology already relates the two classes. One without the other is the common
   failure: the annotation exists, the relation does not, so nothing is derivable.
3. **Every mart declares `meta.grain`,** and is actually unique at it. Test the
   claim rather than trusting it:
   ```sql
   select <grain cols>, count(*) c from <mart> group by all having count(*) > 1 limit 5
   ```
4. **Aggregation lives in the semantic layer, not in marts.** A mart that
   pre-aggregates what a metric also aggregates gives two answers to one question.
   `list_metrics` / `get_dimensions` to see what the semantic layer already owns.

## 3. Layering

staging → intermediate → marts, and sources only entering at staging. Ask the
graph rather than reading files:

```
kg_search "<concept>"          # what exists
kg_neighbors "<node>" depth=2  # what it touches
kg_path "<src>" "<dst>"        # how two things are actually connected
```

Findings: a mart selecting straight from a source, a staging model with business
logic in it, a cycle, or an orphan (a model nothing consumes — dead weight that
still costs build time).

## 4. Boundaries

- Nothing in the project reads `platform/` internals; shared infra is used
  through `pf`, not imported around.
- Nothing references a sister project. Ever.
- Group-level conformed dimensions are used, not re-implemented per sister —
  a re-implementation is how two sisters start disagreeing about a customer.

## 5. Report

For each finding: the claim that is false, the evidence, what breaks because of
it, and the fix. Separate **structural** faults (wrong layering, undeclared join
— fix now) from **drift** (stale annotation, missing grain — schedule). Where a
fix changes a model, give its blast radius from `impact_analysis`.

If a decision is worth keeping, write it to `decisions/ADR-NNNN-*.md` rather than
leaving it in the transcript.

---

## Generic checklist (retained from the source guide)

**Structure** — separation of concerns, circular dependencies, violations of
clean-architecture boundaries, feature-based vs type-based organisation.
**Patterns** — consistency of the patterns in use, composition over inheritance,
error handling at boundaries, state management.
**Evolution** — what will be expensive to change later, what is over-abstracted
now, which decisions deserve an ADR.

**Output format** — analysis, prioritised recommendations, and the trade-offs of
each; note explicitly where the current design is fine and should be left alone.
