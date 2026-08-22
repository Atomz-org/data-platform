# The semantic stack

Four layers, each answering a question the one below it cannot. Built in this
order deliberately: a topology without identity cannot generate a join, and a
policy without an ontology has nothing to attach to.

```
policy.yaml     what must HOLD    intent -> constraint -> artifact -> evidence   (OpenTopology)
topology.yaml   how they RELATE   named relations, domain/range, cardinality     (OWL object properties)
concepts.yaml   what things ARE   classes, identity, datatype properties          (OWL classes)
annotations     where they LIVE   concept/role/links per dlt resource            (per project)
```

Only the bottom layer is per project — with one exception. **Policy also layers,
platform → group → project, and may only ever tighten.** Vocabulary cannot: two
sisters that mean different things by `Payment` cannot be rolled up. Obligations
can and must, because acme-eu answers to GDPR and acme-us does not. See
[POLICY.md](POLICY.md).

The knowledge graph is the join of all four. Everything else is a **projection**
of the graph, never a parallel hand-maintained file:

| Projection | Command | Consumer |
|---|---|---|
| WrenAI MDL | `pf semantic mdl <g> <p>` | BI, text-to-SQL, agents |
| OWL / RDF-XML | `pf semantic owl` | Ontology-Playground, any OWL tool |
| Context card | `pf kg card <g> <p>` | the agent's always-on index |
| Impact report | `pf impact <g> <p> <node>` | the merge gate |

## Why relations are nodes, not edges

A bare edge cannot carry a name, an inverse, or a binding. MDL requires
`relationships[].name`; a reverse-reading agent needs `inverse`; and the physical
join needs to be bound to an actual foreign-key column. So a relation is a node,
with `domain_of` / `range_of` edges into it and a `realises` edge from the column
that implements it.

## How a join condition is derived

Nothing is guessed from a naming convention:

```
Column charges.customer_id --realises--> Relation customer_pays_payment
Relation.range = Customer,  Customer.identity = customer_id
                       ↓
   fct_payments.customer_id = dim_customers.customer_id   [MANY_TO_ONE]
```

Cardinality comes from the relation and is inverted when the foreign key sits on
the range side — the FK is always on the many side.

## Room left for WrenAI

`pf semantic mdl` emits a manifest validated against
`core/wren-mdl/mdl.schema.json` from Canner/WrenAI. To adopt Wren, point it at
`groups/<g>/projects/<p>/mdl/mdl.json`; no modelling work is repeated, because
the manifest is generated from the same graph the agents already query.

Carried into MDL `properties` so nothing is lost in translation:
`pf.role`, `pf.pii` (drives masking), `pf.relation`, `pf.also_realises`,
`grain`, `layer`.

## Undocumented columns

The graph reads physical columns from the warehouse as well as documented ones
from the dbt manifest. Documentation supplies role and PII; introspection
supplies completeness. Without the second, join keys — usually the columns nobody
documents — are invisible, and every projection is missing its relationships.
