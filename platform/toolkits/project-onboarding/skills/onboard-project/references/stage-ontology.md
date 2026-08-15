# Stage 2 — ontology, topology, annotations

**Goal condition:** every raw resource has a concept, roles and links that the
platform ontology validates, and the topology those links traverse resolves.

This stage is first for a reason. Annotations drive generated staging, currency
normalisation, PII policy, the knowledge graph, the MDL projection and the impact
gate. Every later stage reads them. Modelling before annotating means modelling
against a vocabulary nobody has agreed on yet.

## The three artefacts

| Artefact | Where | Answers |
|---|---|---|
| **ontology** | `platform/src/pf/ontology/concepts.yaml` + `groups/<g>/ontology/extension.yaml` | what *kinds of thing* exist |
| **topology** | `platform/src/pf/ontology/topology.yaml` | how those kinds relate, by name and direction |
| **annotations** | `<project>/contracts/annotations.yaml` | which physical column plays which role |

The ontology is warehouse-independent. The binding to actual columns is per
project and lives only in the annotations — which is why the same topology serves
sister companies whose tables look nothing alike.

## Evaluate

```bash
pf align evaluate <group> <project> --stage ontology
```

Findings you will see, and what each means:

- **`no-annotations`** — nothing has meaning yet. Start here.
- **`resource-unannotated`** — a seed or declared source with no entry. Every raw
  table needs one; a mart does not (annotating a derived table asserts it is a
  source of record, which gives a definition two homes).
- **`annotation-invalid`** — the concept, a role or a link does not exist, or a
  `money_amount` has no `currency_code` beside it, or nothing is a key.
- **`annotation-orphaned`** — an annotation naming a resource that is not there.

## Implement

Write `contracts/annotations.yaml`, one entry per raw resource:

```yaml
- resource: raw_orders
  concept: Order
  source: jaffle
  roles: {id: natural_key, ordered_at: event_time, order_total: money_amount,
          currency: currency_code}
  rename: {id: order_id}
  links: {customer_id: Customer, store_id: Location}
  description: One placed order.
  grain: one order
```

Roles are the contract. `pf gen-staging` reads them to emit cleaning; the PII
audit reads them to find unmasked columns; the metric layer reads them to know
which column is the time axis.

### When the ontology has no word for it

This is the interesting case, and it is **not** an annotation bug. A retail
project arrives with suppliers, purchase orders and shipments; a platform
ontology built for subscriptions has none of those concepts.

Do not force a bad fit. Annotating a supplier as `Organization` makes the
validator pass and makes every downstream projection wrong. Instead:

```bash
pf semantic scan <group> <project>       # induce a proposal from what landed
pf semantic review <group> <pid>         # what it would change, and what it unlocks
pf semantic approve <group> <pid> --by <name>
```

`scan` profiles the warehouse and proposes classes, roles and relations with a
confidence per axiom. `review` shows the diff against the current ontology.
`approve` merges the accepted axioms into the **group** extension, not the
platform ontology — a new concept reaches the sisters that need it without
imposing itself on every other company.

**Approving is a human decision.** An ontology extension changes the vocabulary
every project in the group is validated against. Present the proposal, say what
it unlocks, and wait.

## Validate

```bash
pf align validate <group> <project> --stage ontology
pf check <group> <project>              # the same conformance, plus blast radius
```

Four conditions: annotations exist, they conform, the topology conforms, and
every raw resource is annotated.

## Then

`pf gen-staging <group> <project>` writes the 1:1 staging models from these
roles. Run it before the layers stage, not after — it will overwrite hand-written
staging, and losing an hour of layer work to a regeneration is avoidable.
