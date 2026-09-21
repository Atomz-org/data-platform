---
type: Vendor Upstream
title: Forge (wss3-forge)
description: the control plane's component layer and design tokens
resource: https://github.com/Webba-Creative-Technologies/forge
tags:
- vendor
- library
- MIT
status: stable
sources:
- id: forge:skills/forge
  resource: https://github.com/Webba-Creative-Technologies/forge
  title: skills/forge
- id: forge:package.json
  resource: https://github.com/Webba-Creative-Technologies/forge
  title: package.json
- id: forge:DESIGN.md
  resource: https://github.com/Webba-Creative-Technologies/forge
  title: DESIGN.md
---

# Forge (wss3-forge)

The control plane was one hand-written HTML file. That was the right call while it was a diagnostic surface and the wrong one once data owners were expected to edit governance in it: every table, dialog and form was bespoke, and accessibility was whatever the last edit remembered. Forge supplies the component layer and, unusually, ships its own Claude Code skill pack — so the rules for using it are checked in rather than re-derived per session.

## Adopted

- **skills/forge** (data) -> platform/toolkits/forge-ui/skills/forge-ui/SKILL.md
  Registered as a platform skill and read verbatim at authoring time. If upstream renames a component or changes a token, the skill is the thing that goes stale, which is why this is `data` and not `shape`.
- **package.json** (data) -> platform/src/pf/ui/web/package.json
  We install the published `wss3-forge` wheel-equivalent from npm and pin the submodule for provenance, the same split the recce entry documents: the registry is the contract, the package is the artefact we run.
- **DESIGN.md** (shape) -> platform/src/pf/ui/web/src/theme.css
  Token names and the light/dark contract come from here.

## Declined

- **forge's motion primitives on data tables**
  Animated row entry on a table an operator is scanning for a changed number costs reading time and gives nothing back. Motion is kept for overlays and state transitions, where it explains what moved.
