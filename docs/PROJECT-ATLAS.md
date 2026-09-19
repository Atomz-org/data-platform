# The per-project atlas

`docs/kg-atlas.html` is the platform's atlas: fourteen node kinds, fourteen
edges, the traversals between them. Those facts are identical in all eight
projects, which is why they live once at the root.

What that page cannot show is *one* project — which of the fourteen kinds it
actually uses, what its lineage really looks like, which policies it tightened
locally, where it is thin. So each project publishes its own, beside the graph
it draws:

```
groups/<group>/projects/<project>/kg/atlas.html
```

```bash
uv run pf atlas <group> <project>     # publish it now
uv run pf atlas --all                 # every project
uv run pf atlas <g> <p> --config      # what this project resolved to
```

You rarely run these. `pf bootstrap` publishes one, and after that the page
refreshes around the project's own dbt runs.

Code: [`platform/src/pf/atlas.py`](../platform/src/pf/atlas.py).

---

## When it refreshes, and why that is a per-project decision

An atlas is a picture of the **graph**, and the graph is a build artefact: it
describes the last `pf kg build`, not the warehouse. A page generated at the
wrong moment is therefore confidently wrong, and which moment is right depends
on what the project is for:

| Phase | What it captures |
|---|---|
| `after_dbt_run` | the default — models exist, the manifest is fresh, the graph describes what was just built |
| `before_dbt_run` | the state going in, for a run expected to break something |

Both, either or neither. They are independent because they answer different
questions, and with `keep_previous: true` the outgoing page is moved to
`kg/atlas.prev.html` rather than overwritten, so a before/after pair survives
the run that separated them.

### Where the hook attaches

`pf.runtime.dbt_runtime.dbt()` — the one function every dbt invocation in this
platform goes through, `seed.py` and `pf seed` included. Attaching there is what
makes the hook reach every caller without any of them remembering to call it.

It fires only for **`run` and `build`**. `parse`, `deps`, `ls`, `debug` and
`docs` change nothing an atlas would show, and firing on those would put three
identical regenerations in front of every real one.

**A hook can never fail a build.** `_run_hooks` swallows everything. Publishing
a picture of the graph is a convenience; the run is the thing that matters, and
the two must not share a fate. Four ways it could have failed — a path outside
any project, an unparsable config, an unknown phase, a locked graph — are each
covered by a test.

---

## Configuring it

Three layers, later winning key by key — the same shape as `tools.yaml`:

```
platform defaults   pf.atlas.DEFAULTS
group               groups/<group>/atlas.yaml
project             groups/<group>/projects/<project>/atlas.yaml
```

A group that wants every sister publishing an atlas sets it once; a project that
does not want one says so without arguing with its siblings. An override changes
only the keys it names.

```yaml
version: 1
atlas:
  enabled: true
  output: kg/atlas.html
  phases:
    - after_dbt_run
  keep_previous: false
  sections: [census, pipeline, lineage, governance, provenance, gaps]
```

| Key | Does |
|---|---|
| `enabled` | off means nothing is written, by the hook or by `pf atlas` |
| `output` | relative to the project directory |
| `phases` | when to refresh; empty means on request only |
| `keep_previous` | move the outgoing page aside instead of overwriting |
| `sections` | trim to the part this project reads |
| `title` | override the heading |

**An unknown key is refused by name, not ignored.** Silently dropping `enabeld`
is how a typo becomes a setting nobody has and a project quietly publishes
something it opted out of.

---

## What is on the page

| Section | Answers |
|---|---|
| census | which node kinds this project actually has, by plane |
| pipeline | ingest → delivery, with this project's real counts |
| lineage | a real chain, with actual model and metric names |
| governance | its policies, their severity, and **which layer set each** |
| provenance | the inputs the graph was built from, and what reads it |
| gaps | what this graph cannot answer, and the command that fixes it |

A stage holding nothing is drawn grey and labelled *none yet* rather than
dropped, so the page has the same shape in every project and a hole reads as a
hole instead of as an absence the reader has to notice.

The diagrams follow `viz-standards/charts-and-diagrams` and reuse the platform
atlas's plane colours unchanged — pale fill, saturated stroke of the same hue,
near-black ink. Mermaid will not recolour an explicit `classDef` and there is no
media query inside a diagram, so each plate sits on a light card in both themes.

---

## Why it is not committed

`kg/architecture.md` is generated and committed; this is generated and **not**.
The difference is one line on the page: the atlas stamps the graph's build time,
so carrying it would rewrite eight files on every `dbt build` and say nothing.

It is in `.gitignore`, and on the gate's `denylist` so no agent hand-edits a
page the next run overwrites.

---

## Failure modes

| Output | Means |
|---|---|
| `disabled in atlas.yaml` | `enabled: false` somewhere in the layers — `--config` shows which |
| `unknown key(s) [...]` | a typo; the message lists the valid keys |
| `unknown phase(s) [...]` | only `before_dbt_run` and `after_dbt_run` exist |
| `no graph yet` | run `pf seed`, then `pf kg build` |
| page did not refresh after a build | the phase is not enabled, or the command was `parse`/`deps` |
