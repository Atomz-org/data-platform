---
name: forge-ui
description: Building or changing the control-plane UI. Use for ANY React work under platform/src/pf/ui/web — picking a component, theming, layout, tables, forms, or reviewing UI code for accessibility.
---
# Control-plane UI

The control plane is a Vite + React SPA at `platform/src/pf/ui/web`, built to
`platform/src/pf/ui/static/dist` and served by the same FastAPI process that
serves `/api`. There is no second server and no SSR.

## Read the vendored skill first, not the component list

Forge ships its own skill pack and it is pinned as a submodule:

    vendor/forge/skills/forge/SKILL.md      the index
    vendor/forge/skills/forge/components.md every component and its props
    vendor/forge/skills/forge/tokens.md     spacing, colour, radius, motion
    vendor/forge/skills/forge/a11y.md       what the components already handle
    vendor/forge/skills/forge/anti-patterns.md

**Read the props before writing the component.** `wss3-forge` exports 358 names
and TypeScript will reject a guessed prop — `Badge` takes `variant`, not
`color`; `SegmentedControl` options take `id`, not `value`; `Grid` responsive
keys start at `xs`, not `base`. Every one of those was a guess that failed to
compile.

## Which tile

`KpiCard` for a dashboard KPI strip — uppercase label, large value, delta line.
`StatCard` is icon-led and *larger*; used without an icon it renders as a tall
box with the value stranded at the bottom.

## What this platform adds on top

`src/theme.css` holds only what a data console needs and a general component
library has no opinion about: a monospace stack for identifiers, tabular numerals
for any column of figures, and the shared verdict colours. Reach for a Forge
token before adding to it.

Two rules that are ours, not Forge's:

- **Status is never colour alone.** Every verdict renders a dot *and* the word —
  see `src/components/Verdict.tsx`. Screenshots get printed and pasted into
  tickets, and roughly one reader in twelve cannot separate the red from the
  green.
- **A zero is not a result.** Distinguish "checked, found nothing" from "nothing
  checked it". A green nought over an unmeasured project is a clean bill of
  health nobody issued.

## Wide content

Tables scroll inside their own card (`.pf-scroll-x`), never the page. A
horizontally scrolling page takes the sidebar off screen.

## Build

    npm --prefix platform/src/pf/ui/web run build   # writes static/dist
    npm --prefix platform/src/pf/ui/web run dev     # proxies /api to :8787

`static/dist` is generated and gitignored. `pf ui` serves the last build; if it
returns 503, the answer is to build, not to debug the server.
