# OKF — acme/acme-eu

`okf/` is this project's semantic layer as an **Open Knowledge Format** bundle:
one Markdown file with YAML frontmatter per table, per concept and per metric,
and an `index.md` that declares the version and links every one. It is what an
agent, an analyst or a catalogue reads to learn what a table and a column mean
— generated from the MDL, the ontology annotations and the metric definitions
by `pf tool okf build`, validated through the vendored OKF models before a file
is written, and never hand-edited.

```bash
pf tool okf build acme acme-eu     # regenerate from the semantic layer
pf tool okf check acme acme-eu     # stale or non-conformant? exits 1
pf tool okf graph acme acme-eu     # does every page resolve in kg/graph.json?
pf tool okf weave acme acme-eu     # ask the weaver for what the platform lacks
pf tool okf serve                          # the weaver's own API, locally
```

## Where a definition comes from

| In the bundle | Read from |
|---|---|
| a table's description, layer, grain | the model's properties in `mdl/mdl.json` |
| a column's definition | the ontology role on it (`contracts/annotations.yaml`) |
| the concept a table instantiates | the relation the MDL join names, else the class whose identity is the key |
| a metric | `transform/models/semantic/` |
| lineage, policies, decisions on a page | this project's `kg/graph.json` |

Confidence is a fact, not a guess: `1.00` where the platform holds a
declaration, `0.00` where it holds none. A `0.00` is a column to annotate.

## Which tables are in it

The ones the semantic layer exposes: the marts layer, minus what the project
marks `meta: {semantic: false}` in dbt, plus what it marks `true` and any mart
an exposure names. A bundle holds at most 100 tables — a repository whose
`marts/` is a corpus rather than a surface declares which models are the
surface, and `pf semantic mdl --check` keeps the manifest honest about it.

## Joined to the knowledge graph

Each page carries `okf_x_kg_node` — the node in `kg/graph.json` it documents —
and states what only the graph holds: what feeds the table, what reads it
(including the Evidence dashboards), the policies that govern its concept and
the decisions recorded about it. The graph answers back: `kg_neighbors` names
the page that documents a node, and `pf impact` lists the pages a change
stales. Rebuild both together — `pf kg build` then `pf tool okf build` — or
`pf tool okf check` fails on a page whose node the graph no longer holds.

## Connected to the platform

`okf/index.md` names `platform/okf/index.md` — the platform ontology in the
same format — and a concept file links to the platform's when the class is the
platform's, or says `okf_x_defined_in: group` when this family's extension
declared it. Follow the link to the definition every sister shares.

## Weave

`weave` runs OKF Weaver's generator over the tables here and writes
`okf/weave.md`: proposed definitions with the weaver's confidence, next to
what the platform holds. Nothing lands in the bundle from it. Promote a
proposal into an annotation or a model description, rebuild, and it becomes
true. Needs `ANTHROPIC_API_KEY`; recorded in the provenance ledger.
