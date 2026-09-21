---
type: Vendor Upstream
title: Next.js shadcn Admin Dashboard
description: dashboard shell and theme presets, reference only
resource: https://github.com/arhamkhnz/next-shadcn-admin-dashboard-baseui
tags:
- vendor
- reference
- MIT
status: stable
sources:
- id: shadcn-admin:src/app
  resource: https://github.com/arhamkhnz/next-shadcn-admin-dashboard-baseui
  title: src/app
---

# Next.js shadcn Admin Dashboard

Adopted for its layout and theming decisions, not its code: this is a Next.js application and our control plane is a Vite SPA served by the FastAPI that already owns the API. Copying the app would have meant a second long-running server in a Python monorepo to gain screens we do not need. What it is genuinely good at is the shell — collapsible sidebar, grouped navigation, theme presets — and that is what was taken.

## Adopted

- **src/app** (shape) -> platform/src/pf/ui/web/src/App.tsx
  Sidebar-plus-topbar shell, navigation grouped by intent, and the content column that scrolls independently of the rail.

## Declined

- **the Next.js application itself**
  App Router, SSR and a Node server buy nothing here — every screen reads a local FastAPI endpoint on localhost. It would have added a second runtime to deploy and a build story to a repo that had neither.
- **the bundled auth flows and RBAC screens**
  The control plane binds to 127.0.0.1 and is single-operator. Shipping a login form over no authentication would imply a boundary that is not there.
