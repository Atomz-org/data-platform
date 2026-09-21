---
name: agent-scopes-not-vendors
description: AGENTS.md rules go by execution scope (session/autonomous/inline), never vendor; a hand-off is notes+git, not a .agent-memory/ ledger
type: feedback
status: active
agent: claude-code
---

**Why:** the same model runs as a chat session, an Actions job and an inline
completion, and each can do different things (shell? human in the loop? one
file?). Vendor roles (Claude = macro, Copilot = micro) broke the moment
Copilot's coding agent got a shell and `@claude` in Actions lost its human.
A parallel ledger (`.agent-memory/session_state.toon`,
`architecture_graph.toon`, `context_compression.md`) was proposed twice and
declined: every field of a hand-off is already recorded — `agent:` on the
note, `git log`, the branch/PR, `status:`, the commit, a `feedback` note —
the architecture is generated from `kg/graph.json` and CI-checked, and one
mutable file that every concurrent session appends to conflicts on every PR.

**How to apply:** a new tool gets a row in the entry-points table of
`AGENTS.md` and, if it leaves no environment mark, `export PF_AGENT=<name>`;
`detect_agent()` in `pf/memory.py` knows `PF_AGENT`, `CLAUDECODE`,
`GEMINI_CLI`, `GITHUB_ACTIONS`. Add a per-vendor rules file only when the
tool cannot read `AGENTS.md` (`GEMINI.md` and `.github/copilot-instructions.md`
exist for that reason alone; each is a pointer plus that tool's scope
mapping). Asked for `.agent-memory/` again: `AGENTS.md` §5 hand-off table
and §7.
