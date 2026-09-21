---
type: Vendor Upstream
title: Recce Claude Plugin
description: Recce's own agent skills, agents and MCP wiring
resource: https://github.com/DataRecce/recce-claude-plugin
tags:
- vendor
- skills
- MIT
status: stable
sources:
- id: recce-claude-plugin:plugins/recce/skills/recce-review
  resource: https://github.com/DataRecce/recce-claude-plugin
  title: plugins/recce/skills/recce-review
- id: recce-claude-plugin:plugins/recce/agents/recce-reviewer.md
  resource: https://github.com/DataRecce/recce-claude-plugin
  title: plugins/recce/agents/recce-reviewer.md
---

# Recce Claude Plugin

Upstream has already written down how an agent should drive Recce — which checks to run for a schema change, when a diff is inconclusive. That is the same shape as `platform/toolkits/`, so it is a source for our toolkit rather than something to invent.

## Adopted

- **plugins/recce/skills/recce-review** (port) -> platform/toolkits/recce-review/skills/recce-review/SKILL.md
  The review workflow — baseline, run, read the diff, decide — ported to our toolkit format and to `pf tool recce` instead of bare `recce`.
- **plugins/recce/agents/recce-reviewer.md** (shape) -> platform/toolkits/recce-review/skills/recce-review/SKILL.md
  The reviewer's stopping rule — a diff you cannot explain is a finding, not noise.

## Declined

- **plugins/recce/hooks/ and settings/defaults.json**
  Session hooks and permissions are already the platform's: `gate.yaml` and the PreToolUse hook decide what an agent may write. A second hook system layered underneath is how a gate ends up with two answers.
- **servers/recce-docs-mcp**
  Documentation search. `pf mcp` serves the graph; docs are a browser tab.
