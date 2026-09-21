---
type: Vendor Upstream
title: Recce UI
description: React component library behind the Recce review UI
resource: https://github.com/DataRecce/recce-ui
tags:
- vendor
- reference
- Apache-2.0
status: stable
sources:
- id: recce-ui:package.json
  resource: https://github.com/DataRecce/recce-ui
  title: package.json
---

# Recce UI

Pinned so the embedded review pane can be built against a known version of the components, and so a breaking change upstream is visible here rather than as a blank iframe.

## Adopted

- **package.json** (parity) -> platform/src/pf/tools/recce.py
  The version here and the `recce` package version must agree — the server serves a bundle built from these components, and a mismatch shows up as a UI that loads but cannot talk to its own API.

## Declined

- **Building our own review pane from the component library**
  `recce server` already serves a UI built from exactly these components. Rebuilding it would add a pnpm toolchain to a Python platform to reproduce something upstream ships working. We embed the server and keep the library pinned so the option stays open.
