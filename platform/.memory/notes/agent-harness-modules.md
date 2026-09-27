---
name: agent-harness-modules
description: one hook core (pf.agenthook) for every harness; a harness = one module in pf.harnesses; never hand-edit generated configs
type: feedback
status: active
agent: claude-code
---

stack: [pf.agenthook, pf.harness_adapters, pf.harnesses.<name>, platform/hooks/agent_hook.py]

Why: every harness now reaches the same gate/permissions/provenance through its own hook
system; the per-vendor parts are only dialect (payload in, "no" out) and config rendering.

How to apply:
- A new harness = one module in platform/src/pf/harnesses/ declaring SPEC, plus a SAMPLES
  entry in platform/tests/gate/test_agent_hooks.py and a case in bin/agent-here. Never edit
  pf.harness lists — HARNESSES/TARGETS are computed from the registry.
- A scorecard row may say "hook" only if its hook_config is rendered and calls
  `agent_hook.py <key> pre` — test_harness enforces it.
- Never hand-edit generated configs or .agents/skills links; `uv run pf context refresh`.
- Claude's own permission lists are NOT applied by the core for harness "claude" (Claude does it);
  for every other harness they are, from .claude/settings.json + the project's.
