# The semantic stack

Four layers, each answering a question the one below it cannot. Built in this
order deliberately: a topology without identity cannot generate a join, and a
policy without an ontology has nothing to attach to.

```
policy.yaml     what must HOLD    intent -> constraint -> artifact -> evidence   (OpenTopology)
                                  ...and `controls:`, the external ids each policy
                                  discharges (`AIR-DET-21`) — see docs/AIR.md
topology.yaml   how they RELATE   named relations, domain/range, cardinality     (OWL object properties)
concepts.yaml   what things ARE   classes, identity, datatype properties          (OWL classes)
annotations     where they LIVE   concept/role/links per dlt resource            (per project)
```

Only the bottom layer is per project — with one exception. **Policy also layers,
platform → group → project, and may only ever tighten.** Vocabulary cannot: two
sisters that mean different things by `Payment` cannot be rolled up. Obligations
can and must, because acme-eu answers to GDPR and acme-us does not. See
[POLICY.md](POLICY.md).

The knowledge graph is the join of all four — its node kinds, its legal edges and
the traversals that answer real questions are mapped in [KG-ATLAS.md](KG-ATLAS.md).
Everything else is a **projection** of the graph, never a parallel
hand-maintained file:

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

## WrenAI, adopted

`pf semantic mdl` emits a manifest validated against
`core/wren-mdl/mdl.schema.json` from Canner/WrenAI, and `pf.tools.wren` points
current WrenAI — a CLI over MDL, no web UI — at it. Beside each manifest the tool
generates the workspace Wren's CLI reads, `mdl/wren/`, from the same tracked
inputs (the manifest, the ontology, the graph): `wren_project.yml`, the
LLM-facing `target/mdl.json` with every column classified as personal data
*removed* (and every relationship, cube measure and view that read it), the
rules an agent is handed under `knowledge/rules/`, and the questions it has
answered before under `knowledge/sql/`. `pf tool wren check --all` holds the
tracked half current in CI, the way `pf semantic mdl --check --all` holds the
manifest.

Every `wren` process runs inside that workspace with Wren's home pointed at
it, so one project's memory is never another's. Every question takes one road,
`pf.tools.wren_gate`: policy (one read-only SELECT, judged by statement type),
plan (`wren dry-plan` against the LLM-facing manifest), dry-run (`EXPLAIN` on
the project's warehouse, read-only — Wren's own dry-run cannot see dbt's
schemas through its DuckDB file scanner), execute (row-limited, through the
platform's `Warehouse`, never a second connection), and a `wren-query` entry in
the group's `loop-ledger.json` whichever way it went. The fourth attempt at a
statement that failed three times is refused with "escalate". The
`wren-analytics` toolkit is the procedure an agent follows on that road, and the
`wren_context` / `wren_query` / `wren_cube` MCP tools are the road itself.

Cubes are one per model that carries metrics (`<model>_metrics`), holding only
that model's measures and dimensions: a single project-wide cube handed its
base object measures from other facts, which planned and then failed to bind.
A cube question (`wren_cube`, `pf tool wren cube`) is translated to one SELECT
by `wren cube query --sql-only` and then takes the same gated road.
`pf tool wren check` plans every cube with all its measures and, where a
warehouse exists, binds the plan with `EXPLAIN`.

Carried into MDL `properties` so nothing is lost in translation:
`pf.role`, `pf.pii` (drives masking in BI, removal in the workspace),
`pf.relation`, `pf.also_realises`, `grain`, `layer`.

## Undocumented columns

The graph reads physical columns from the warehouse as well as documented ones
from the dbt manifest. Documentation supplies role and PII; introspection
supplies completeness. Without the second, join keys — usually the columns nobody
documents — are invisible, and every projection is missing its relationships.
