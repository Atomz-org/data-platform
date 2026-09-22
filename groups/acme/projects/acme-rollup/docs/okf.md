# OKF — acme/acme-rollup

`okf/` is this project's semantic layer as an **Open Knowledge Format** bundle:
one Markdown file with YAML frontmatter per table, per concept and per metric,
and an `index.md` that declares the version and links every one. It is what an
agent, an analyst or a catalogue reads to learn what a table and a column mean
— generated from the MDL, the ontology annotations and the metric definitions
by `pf tool okf build`, validated through the vendored OKF models before a file
is written, and never hand-edited.

```bash
pf tool okf build acme acme-rollup     # regenerate from the semantic layer
pf tool okf check acme acme-rollup     # stale or non-conformant? exits 1
pf tool okf weave acme acme-rollup     # ask the weaver for what the platform lacks
pf tool okf serve                          # the weaver's own API, locally
```

## Where a definition comes from

| In the bundle | Read from |
|---|---|
| a table's description, layer, grain | the model's properties in `mdl/mdl.json` |
| a column's definition | the ontology role on it (`contracts/annotations.yaml`) |
| the concept a table instantiates | the relation the MDL join names, else the class whose identity is the key |
| a metric | `transform/models/semantic/` |

Confidence is a fact, not a guess: `1.00` where the platform holds a
declaration, `0.00` where it holds none. A `0.00` is a column to annotate.

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
