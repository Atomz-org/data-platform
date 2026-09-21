---
name: group-shared-python-by-path
description: Group-shared Python (groups/<g>/shared/python) is found via pf.runtime.paths, never added to the uv workspace glob
type: project
status: active
agent: claude-code
---

`groups/commodity/shared/python/src/commodity_shared` holds the connectors and
catalog loader every commodity sister imports. It is deliberately NOT a uv
workspace member: a `groups/*/shared/python` glob in the root pyproject makes
uv error ("missing a pyproject.toml") whenever the directory exists without the
file — which happens after any checkout of a branch lacking it, because
`__pycache__` lingers — and that bricks every `uv run` hook (see
[[uv-workspace-hook-deadlock]]). Project packages are not installed either;
everything is found by path: `pf.runtime.paths.extend_sys_path(project_dir)`
(used by seed.py and by `build_definitions`).

**Why:** tested on 2026-09-20 — the glob member errored exactly as feared with
the pyproject moved aside.
**How to apply:** when a group needs shared code, put it under
`shared/python/src`, import it after `extend_sys_path`, and run its tests with
`uv run pytest groups/<g>/shared/python/tests` (conftest adds src to sys.path).
Never declare it as a dependency in a sister's pyproject.
