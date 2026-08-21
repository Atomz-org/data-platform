# The knowledge graph, as a map

The graph answers questions about *this project*. It cannot tell you what it is
made of.

That second half is what this file is. It is identical in all eight projects, so
paying for it in every budgeted context card would be eight times the right
price — and leaving it out is how a traversal gets written backwards.

Code: [`platform/src/pf/kg/`](../platform/src/pf/kg/) — `store.py` (the two
tables), `build.py` (what fills them), `query.py` and `impact.py` (what an agent
calls). See also [SEMANTICS.md](SEMANTICS.md) for the four layers the graph is
the join of, and [POLICY.md](POLICY.md) for how its governance plane is
resolved.

---

## Where this sits among the context tiers

| Tier | What it holds | Cost |
|---|---|---|
| Always on, **budgeted** | `CLAUDE.md`, `kg/context_card.md`, the group card | every request, for the life of the project |
| On demand | toolkit skills | only when the description matches |
| **Queried, never loaded** | the knowledge graph | one tool call |

The card is regenerated per project and lists *instances* — acme-us has three
raw tables and six metrics. It never says that `realises` runs Column → Relation,
that `impact_analysis` ignores the semantic plane, or that `kg_path` walks edges
in both directions. Those are properties of the graph itself, and they are what
this file records.

`pf tokens` enforces the budgets: 1500 tokens for a project card, 400 for a
group card. This file is not in any of them. Read it once.

---

## Three planes, one store

Two DuckDB tables hold everything — `kg_nodes` and `kg_edges`. The structure
lives in the `kind` column, and it divides into three planes: what physically
exists, what it means, and what must hold of it.

```mermaid
flowchart LR
  subgraph PHY["PHYSICAL / ANALYTICAL — what exists, and what it feeds"]
    direction TB
    SO[Source]
    TA[Table]
    MO[Model]
    CL[Column]
    ME[Metric]
    DI[Dimension]
    TE[Test]
    EX[Exposure]
    PJ[Project]
    SO -->|contains| TA
    TA -->|feeds| MO
    TA -->|has_column| CL
    MO -->|has_column| CL
    MO -->|feeds| MO
    MO -->|measures| ME
    MO -->|grouped_by| DI
    MO -->|tested_by| TE
    MO -->|feeds| EX
    ME -->|feeds| ME
  end

  subgraph SEM["SEMANTIC — what those things mean"]
    direction TB
    CO[Concept]
    PP[Property]
    RE[Relation]
    CO -->|has_property| PP
    CO -->|domain_of| RE
    RE -->|range_of| CO
  end

  subgraph GOV["GOVERNANCE — what must hold"]
    direction TB
    PO[Policy]
    EV[Evidence]
    PO -->|evidenced_by| EV
  end

  TA -->|instantiates| CO
  CL -->|links_to| CO
  CL -->|realises| RE
  PO -->|governs| CO

  classDef phy fill:#d9f4ee,stroke:#0f766e,stroke-width:1.4px,color:#0b0b0b
  classDef sem fill:#e9e1fb,stroke:#5b21b6,stroke-width:1.4px,color:#0b0b0b
  classDef gov fill:#e0e6ed,stroke:#334155,stroke-width:1.4px,color:#0b0b0b
  classDef orphan fill:#f2f6f5,stroke:#93a5a1,stroke-width:1.2px,stroke-dasharray:4 3,color:#0b0b0b

  class SO,TA,MO,CL,ME,DI,TE,EX phy
  class CO,PP,RE sem
  class PO,EV gov
  class PJ orphan

  style PHY fill:#f4fbf9,stroke:#0f766e,stroke-dasharray:5 4,color:#0b0b0b
  style SEM fill:#f8f5fe,stroke:#5b21b6,stroke-dasharray:5 4,color:#0b0b0b
  style GOV fill:#f4f6f9,stroke:#334155,stroke-dasharray:5 4,color:#0b0b0b
```

All fourteen node kinds and all fourteen edge kinds are on that diagram. Nothing
is declared in `NODE_KINDS` or `EDGE_KINDS` that the builder does not emit,
because a declared-but-unbuilt kind is worse than no vocabulary: it makes
traversals that filter on it look implemented when they are dead.

**Project** is dashed because it is an anchor with no edges at all — one node per
graph, carrying group and path in its props, reachable only by id.

The four edges that cross plane boundaries — `instantiates`, `links_to`,
`realises`, `governs` — are the point of the design. They are what let a
semantic or governance question be answered by walking, rather than by reading
three YAML files.

### Colour is fixed, not themed

Mermaid will not recolour an explicit `classDef` fill, and GitHub renders one
source on both a light and a dark page. So every diagram here follows the
`viz-standards` rule: **pale fill, saturated stroke of the same hue, near-black
ink**. A fill picked to look right on white is unreadable on black and there is
no media query inside a diagram to save it.

---

## Every edge runs upstream → downstream

This is a contract, not a convention. `out_edges(n)` is always *"what depends on
n"* and `in_edges(n)` is always *"what n was built from"*, with no per-kind
exceptions to memorise.

`feeds` is named for that direction: a staging model *feeds* a mart. It was once
called `derives_from`, which pointed the other way and made every rendered
lineage path read backwards.

One edge kind is deliberately walked *against* the arrow: `has_column`. Changing
a column implicates the model that owns it, so impact analysis follows it upward.
It is the single exception and is encoded as one, in `UPWARD_KINDS`.

| Edge | Runs | Means | Impact walks it |
|---|---|---|---|
| `contains` | Source → Table | a dlt source landed this table | no |
| `has_column` | Table/Model → Column | column belongs to it | **upward** |
| `feeds` | Table/Model/Metric → Model/Metric/Exposure | lineage; the general dependency edge | **yes** |
| `measures` | Model → Metric | a measure on this model backs the metric | **yes** |
| `grouped_by` | Model → Dimension | the semantic model exposes this dimension | **yes** |
| `tested_by` | Model → Test | a dbt test covers it | **yes** |
| `instantiates` | Table → Concept | this table is a physical `Payment` | no |
| `has_property` | Concept → Property | datatype property of the class | no |
| `domain_of` | Concept → Relation | the relation starts here | no |
| `range_of` | Relation → Concept | the relation ends here | no |
| `realises` | Column → Relation | the physical FK behind the relation | no |
| `links_to` | Column → Concept | declared FK target | no |
| `governs` | Policy → Concept | this rule constrains that class | no |
| `evidenced_by` | Policy → Evidence | what proves the rule ran | no |

> **Read the last column before trusting a blast radius.** `impact_analysis`
> traverses **five of the fourteen** edge kinds. It is a lineage instrument, not
> a governance one: a change that breaks a `governs` or `realises` relationship
> comes back *safe to change*, because those edges were never walked. For
> semantic or policy consequences use `kg_neighbors` and read the plane directly.

---

## Four questions, as edge chains

Each of these was run against `groups/acme/projects/acme-us` and is reproduced
from its actual output.

### 1. How does a raw column reach a business metric?

```
col:table:stripe.charges.amount
  --has_column-->  Table  table:stripe.charges
  --feeds------>   Model  model:stg_stripe__charges
  --feeds------>   Model  model:fct_payments
  --measures--->   Metric metric:revenue
```

### 2. Why is this column a join key, and to what?

Nothing is inferred from a naming convention. The foreign key is bound to the
named relation it realises, and the relation carries the cardinality — inverted
when the key sits on the range side, because the FK is always on the many side.

```
col:table:stripe.charges.customer_id
  --realises-->   Relation customer_pays_payment
                  props: from_concept=Payment, to_concept=Customer,
                         fk_column=customer_id, fk_table=charges,
                         cardinality, reverse
  Relation --range_of--> Concept Customer   (identity: customer_id)
                  => fct_payments.customer_id = dim_customers.customer_id
```

### 3. Is this rule enforced, and what proves it?

The OpenTopology chain — intent → constraint → artifact → evidence — is in the
graph so that *"does anything check this"* is a traversal rather than an
archaeology exercise across three YAML files.

```
policy:entity-requires-identity
  --governs------>  Concept  concept:Customer
  --evidenced_by->  Evidence evidence:impact_reports

  props.enforced_by = []   =>  NOTHING enforces it. That is the finding.
```

### 4. Is it safe to change this?

One `has_column` hop upward, then everything downstream. Severity is structural,
not a judgement call: any exposure or metric in the radius is *breaking*, models
alone are *review*, nothing is *safe*.

```
impact_analysis("col:table:stripe.charges.amount")

⛔ affects 14 downstream object(s) — severity: BREAKING
   Models (3)      fct_payments, fct_revenue, stg_stripe__charges
   Metrics (5)     aov, gross_payment_volume, payment_count,
                   revenue, revenue_mom_growth
   Dimensions (5)  country_code, customer_segment, paid_at,
                   payment_status, plan_tier
   Exposures (1)   exec_weekly_dashboard  ← owner: Finance
   Tests that will re-run: 7
```

---

## Which tool to reach for

```mermaid
flowchart TD
  Q{"what do you have<br/>to start from?"}

  Q -->|a word, not an id| S["kg_search(term, kinds)"]
  Q -->|one node id| N["kg_neighbors(node, depth)"]
  Q -->|two node ids| P["kg_path(src, dst)"]
  Q -->|a node about to change| I["impact_analysis(node)"]
  Q -->|a business question| M["query_metrics(metrics, group_by)"]

  S --> S1["substring over name, label and id<br/>case-insensitive · caps at 40"]
  N --> N1["UNDIRECTED · both in and out edges<br/>narrow with kinds= before raising depth"]
  P --> P1["UNDIRECTED shortest path, max 8 hops<br/>arrows show chain order, NOT edge direction"]
  I --> I1["walks 5 edge kinds only<br/>records to obs · returns owners to notify"]
  M --> M1["a governed definition, never raw SQL<br/>say which metric is missing instead"]

  classDef q fill:#e0e6ed,stroke:#334155,stroke-width:1.4px,color:#0b0b0b
  classDef tool fill:#d9f4ee,stroke:#0f766e,stroke-width:1.4px,color:#0b0b0b
  classDef gotcha fill:#f6f4fb,stroke:#7c5cc4,stroke-width:1.2px,stroke-dasharray:4 3,color:#0b0b0b

  class Q q
  class S,N,P,I,M tool
  class S1,N1,P1,I1,M1 gotcha
```

The dashed boxes are the behaviours that most often produce a wrong reading. Two
are worth committing to memory.

**Both traversal tools are undirected.** `kg_search` and `kg_path` walk
`out_edges` *and* `in_edges`, which is what makes them useful for "how are these
two things related" but means neither respects the direction contract.

**`kg_path` renders chain order, not edge direction.** Every hop prints as
`--kind-->` regardless of which way the edge actually ran, so the first hop of
recipe 1 above prints `Column --has_column--> Table` — the opposite of the stored
direction. The chain is correct; the arrow is not lineage.

Every one of these returns a compact string on purpose. The MCP truncation
policy — schema plus at most twenty rows plus summary stats, never a raw dump —
applies to every data-returning tool on the server.

---

## Where the graph comes from

```mermaid
flowchart LR
  A1["contracts/annotations.yaml<br/>exported by dlt sources"]
  A2["transform/target/manifest.json<br/>dbt models, columns, tests, exposures"]
  A3["transform/target/semantic_manifest.json<br/>MetricFlow metrics and dimensions"]
  A4["project ontology<br/>concepts + topology + resolved policy"]
  A5["data/&lt;project&gt;.duckdb<br/>information_schema"]

  B["pf kg build"]
  G[("kg/graph.duckdb<br/>kg_nodes · kg_edges")]

  C1["kg/context_card.md"]
  C2["MDL · OWL · otop"]
  C3["impact gate"]
  C4["kg_search / kg_neighbors / kg_path"]

  A1 --> B
  A2 --> B
  A3 --> B
  A4 --> B
  A5 --> B
  B --> G
  G --> C1
  G --> C2
  G --> C3
  G --> C4

  classDef src fill:#d9f4ee,stroke:#0f766e,stroke-width:1.4px,color:#0b0b0b
  classDef onto fill:#e9e1fb,stroke:#5b21b6,stroke-width:1.4px,color:#0b0b0b
  classDef build fill:#e0e6ed,stroke:#334155,stroke-width:1.6px,color:#0b0b0b
  classDef store fill:#fdf6e3,stroke:#8a6d1f,stroke-width:1.6px,color:#0b0b0b
  classDef out fill:#f4fbf9,stroke:#0f766e,stroke-width:1.2px,stroke-dasharray:4 3,color:#0b0b0b

  class A1,A2,A3,A5 src
  class A4 onto
  class B build
  class G store
  class C1,C2,C3,C4 out
```

Every input is optional and the builder degrades quietly, which is exactly why a
thin graph is not obviously a broken one. The build is destructive by design:
`reset()` empties both tables first, so a graph is never a merge of two eras.

### The ontology is resolved at *project* scope

`build_graph` calls `load_project_ontology`, not `load_group_ontology` and not
`load_ontology`. Both narrower choices were bugs, one layer apart:

- Building from the **platform** ontology silently drops every class a steward
  approved into `groups/<g>/ontology/extension.yaml`, so an approved term is
  unusable by dbt, Wren, BI or an agent.
- Building from the **group** ontology drops the project's policy overlay. The
  governance plane is what an agent walks to ask *"what constrains this"*, and at
  group scope it answers with the family's floor — so a project that raised a
  severity, or declared an obligation of its own, was governed by rules its own
  graph did not contain.

Concretely, `acme-eu` declares a GDPR erasure path and raises
`mart-declares-grain` to `error`. Its graph carries eleven Policy nodes; every
sister carries the ten-rule floor:

```console
$ uv run pf kg build acme acme-eu
  Policy   11
$ uv run pf kg build acme acme-us
  Policy   10
```

Each Policy node carries a **`scope`** prop — `platform`, `group:<g>` or
`project:<g>/<p>` — recording which layer set that severity. Severity alone
cannot distinguish an obligation this project took on from one the whole platform
carries, and those warrant different conversations. It is the graph's copy of the
`set by` column in `pf semantic policy`.

Vocabulary deliberately does **not** layer this far; see
[POLICY.md](POLICY.md#what-is-deliberately-not-layered).

### Three ways the graph is thinner than reality

**A missing dbt manifest is silent.** No manifest means no Model nodes, and every
blast radius over that graph returns empty — *"safe to change"* for a change it
could not see. The CI gate refuses rather than passing: `gate()` raises
`GateNotExercised` when the graph holds zero models, because a green tick meaning
"found nothing" is worse than no gate, since it is trusted. `pf kg build` parses
the dbt project first for the same reason.

**Undocumented columns are backfilled, not documented.** The manifest lists only
columns someone wrote a description for — and join keys are usually the columns
nobody documents. The builder reads `information_schema` to fill the gap,
skipping `_dlt_*` and inferring only structural roles from the name. It never
infers PII: that must be declared. So a backfilled column carries
`documented: false` and `pii: false`, and the second flag means *not declared*,
not *not sensitive*.

**Edges to nodes that were never built are dropped.** The last step before
writing filters every edge to those whose endpoints both exist. This keeps the
store consistent, and it means a missing input removes edges silently rather than
leaving dangling ones to trip over.

---

## What a healthy graph looks like

Two projects three orders of magnitude apart, so an empty or lopsided graph is
recognisable as one. Both counts are from the rebuild on 2026-08-21.

| Node kind | Plane | acme-us | jaffle-shop | Reads as |
|---|---|---:|---:|---|
| `Column` | physical | 73 | 10294 | documented + backfilled from `information_schema` |
| `Property` | semantic | 59 | 298 | datatype properties of the concepts |
| `Model` | physical | 7 | 1058 | staging + marts |
| `Concept` | semantic | 16 | 68 | the whole group vocabulary, not only what is used |
| `Relation` | semantic | 17 | 14 | named, with inverse and cardinality |
| `Metric` | physical | 6 | 19 | simple, ratio and derived |
| `Policy` | governance | 10 | 10 | resolved at project scope |
| `Evidence` | governance | 9 | 9 | declared evidence kinds |
| `Dimension` | physical | 8 | 25 | MetricFlow dimensions |
| `Test` | physical | 18 | 532 | dbt tests |
| `Table` | physical | 3 | 57 | raw, one per annotated dlt resource |
| `Exposure` | physical | 2 | 6 | where impact analysis finds a human |
| `Source` | physical | 1 | 1 | the dlt source |
| `Project` | physical | 1 | 1 | anchor node, no edges |
| **total** | | **230** | **12392** | edges: 250 and 13361 |

Three readings worth taking. **Concept far exceeding Table is normal** — the
vocabulary belongs to the group and a project instantiates only the part of it
it needs, so 16 concepts against 3 tables is health, not drift.

**The semantic plane does not scale with the physical one.** jaffle-shop has 151×
the models of acme-us and *fewer* relations — 14 against 17. Relations come from
the group topology, not from the warehouse, so a large project is not
automatically a richly-modelled one. A thousand models joined by fourteen named
relations is where to look for undeclared joins.

**Zero of any kind is the signal.** No Model means the dbt manifest was never
parsed and the gate cannot run; no Metric means every business question falls
back to raw SQL; no Exposure means impact analysis stops at the mart and never
reaches a human to notify. The context card raises the last two as known gaps for
exactly that reason.

---

## What the graph will never tell you

**Anything about a sister.** Graphs are per project and hold no cross-project
edges, so a sister's dependency on a change here is invisible — not merely
unqueried. Sisters share the group ontology, never a graph. Cross-entity blast
radius is assessed in the `<group>-rollup` project, against its own graph, and
nowhere else.

**Business logic.** That a `Payment` has an amount, a currency and an event time
is vocabulary, and it is in the graph. *How acme-us recognises revenue* is
business logic, and it lives in project-confined dbt models. The distinction is
why two sisters can share a word without sharing a definition — and why an
assumption carried across is a bug rather than a shortcut.

**Freshness.** The graph is a build artefact of the last `pf kg build`. It has no
clock and reports no staleness, so a graph built before a model landed will
answer confidently and wrongly. When an answer contradicts a file you can see,
the graph is the stale one.

---

## Rebuilding

```bash
uv run pf kg build <group> <project>    # parses dbt first if no manifest
uv run pf kg card  <group> <project>    # regenerate the card, never hand-trim it
uv run pf tokens                        # the card budgets, enforced
```

`kg/graph.duckdb` and `kg/context_card.md` are gitignored and rebuilt locally.
`kg/graph.json` is tracked, so a graph change is reviewable in a diff.
