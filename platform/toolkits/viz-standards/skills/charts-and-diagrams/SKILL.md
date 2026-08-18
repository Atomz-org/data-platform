---
name: charts-and-diagrams
description: Any chart or diagram — an Evidence page, a mermaid diagram in a PR comment or doc, a plot in a notebook.
---
# Charts and diagrams

Pick the form first and the colour last. Most bad charts are chosen the other way
round, and no palette rescues the wrong form.

## Form
- The data's job picks the type: magnitude → bar, change over time → line,
  polarity → diverging, a single headline → a stat tile and no chart at all.
- Never a dual-axis chart. Two measures of different scale become two charts,
  small multiples, or an index to a common base. This is the most common chart
  mistake in the wild.
- A node-link diagram (mermaid) is for *structure* — what flows into what. If the
  answer is a quantity, it is a chart, not a diagram.

## Colour, by the job it does
- **Categorical** (identity): a fixed hue order, assigned in order and never
  cycled. Colour follows the entity, never its rank — a filter that changes the
  series count must not repaint the survivors.
- **Sequential** (magnitude): one hue, light → dark. Never a rainbow.
- **Diverging** (polarity): two opposed hues with a neutral grey midpoint. Never a
  hue at the midpoint.
- **Status** (state): good / warning / serious / critical are *reserved*. Never
  reuse one for "series 4", or a red mark stops meaning danger.
- Never colour alone. Every status carries an icon or a word; ≥2 series get a
  legend. Text wears text colours, never the series colour.

## Mermaid that GitHub renders
GitHub renders one mermaid source on both a light and a dark page, and does **not**
recolour an explicit `classDef` fill. This drives everything else:

- Use a **pale fill + saturated stroke of the same hue + near-black ink**. The fill
  is then theme-invariant and legible on both. A saturated fill picked for white
  is unreadable on black, and there is no media query to save it.
- Style subgraphs explicitly. Mermaid's default subgraph fill is a yellow that
  reads as *warning* and collides with the reserved status hues.
- **Escape every interpolated string**: `#` opens an entity reference and `"` ends
  the label — both are parse errors, and a diagram that does not parse renders as
  a red box while the surrounding job still exits 0. `<` and `>` are worse than
  errors: `htmlLabels` is on, so an owner written `Name <addr@host>` has the
  address parsed as a tag and *silently dropped*.
- **Never derive a node id from data.** Generate synthetic ids. Two boxes sharing
  an id do not error — mermaid merges them, so one layer quietly vanishes.
- Cap what you draw. Aggregate past a handful of nodes and defer the detail to a
  table; a diagram with sixty boxes is read by nobody.

`platform/src/pf/pr.py` is the worked example — the per-PR architecture chart,
with the palette and every escape in one place.

## Evidence pages
- Pages never restate business logic; every number traces to a compiled metric.
  See the `evidence-bi` toolkit — this skill governs the *visual* choices only.
- Re-divide ratios as `sum(num)/sum(den)`, never `avg(ratio)`.

## Validate, do not eyeball
Colourblind safety is computable, so compute it. Hold a categorical palette to:
adjacent-pair CVD ΔE ≥ 8 and normal-vision ΔE ≥ 15 (OKLab ×100), and text
contrast ≥ 4.5:1 against the surface it actually renders on — the *rendered*
surface, not an assumed white.

Then render it and look at it. The numbers do not catch label collisions,
overflow, or a diagram that is technically correct and unreadable.

---
Provenance: the method here (form-then-colour, the four colour jobs, the CVD and
contrast gates) is adapted from Anthropic's bundled `dataviz` skill. It is not a
vendored upstream — it ships with the agent, not with this repo, so there is no
pin to diff against and it is deliberately absent from
`platform/src/pf/vendor/registry.yaml`, whose every entry must be a submodule.
The palette values here are this platform's own.
