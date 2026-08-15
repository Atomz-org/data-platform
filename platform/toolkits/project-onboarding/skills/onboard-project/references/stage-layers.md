# Stage 4 — staging, marts, semantic

**Goal condition:** every model sits in the layer whose rules it obeys.

Four layers, and each is a *contract*, not a folder:

| Layer | Rule | Materialisation |
|---|---|---|
| `staging` | 1:1 with a raw table. Rename, cast, clean. **No joins, no aggregation.** | view |
| `marts` | Declares a grain. Joins and aggregates. What the business reads. | table |
| `semantic` | MetricFlow YAML. No compiled SQL. | — |
| `utils` | Machinery — the time spine, helpers. Not business logic. | view |

Every rule downstream is keyed on these. The knowledge graph derives lineage
depth from them, the PII audit only flags columns reaching a *mart*, the impact
gate weighs a mart change more heavily, and the semantic layer treats whatever is
in `marts/` as measurable. A model in the wrong layer is not untidy — it is
reasoned about wrongly by four different tools.

## Evaluate

```bash
pf align evaluate <group> <project> --stage layers
```

- **`layer-foreign`** — a directory this platform does not know. `intermediate/`
  is the usual one.
- **`layer-unconfigured`** — a populated layer with no block in
  `dbt_project.yml`, so it builds with dbt's defaults instead of the platform's.
- **`staging-not-1to1`** — a staging model reading more than one upstream.
- **`layer-none`** — a model directly in `models/`, invisible to every rule keyed
  on a layer.

## Implement

### `intermediate/` → `marts/`

The common case, and the mapping is not a demotion. An intermediate model is a
mart that nothing exposes yet: it joins, it aggregates, it has a grain. The
distinction between "internal" and "published" is real but it is a *tag*, not a
directory — put it in `+tags: ['type:intermediate']` and the graph can still tell
them apart while every layer rule keeps working.

```bash
git mv transform/models/intermediate/<sub> transform/models/marts/<sub>
```

Then **re-key the config**. `dbt_project.yml` blocks are keyed by directory:
after the move, an `intermediate:` block names a directory that no longer exists
and every tag under it silently stops applying. This is the failure that leaves
no error message — the build is green and the tags are gone.

### Staging that joins

A join in staging hides a business decision in a layer the platform treats as
mechanical, and `pf gen-staging` will overwrite it on the next run. Move it to
`marts/` and leave a 1:1 staging model behind if the raw table needs cleaning.

### Layers that are neither

`utilities/` → `utils/`. A date spine is machinery. If it has a grain and a
business meaning, it is a mart.

## Validate

```bash
pf align validate <group> <project> --stage layers
```

Three conditions: every model in a known layer, every populated layer configured,
and staging 1:1 with raw.

Then confirm the config survived the move — not by reading the YAML, by reading
the manifest:

```bash
dbt parse --project-dir transform --profiles-dir transform
python -c "import json; m=json.load(open('transform/target/manifest.json')); \
  print(sum(1 for n in m['nodes'].values() if n['tags']))"
```

A drop in tagged nodes after a move means a config block is keyed to a directory
that no longer exists.

## Then

The metrics stage measures what is now in `marts/`. Moving a model after
declaring a semantic model against it breaks the `ref()`, so finish here first.
