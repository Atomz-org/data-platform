# power-tools

The session layer: what a Claude Code session in this repo is *given* (tools,
context, formatting, notifications) as opposed to what it knows how to do. Every
other toolkit teaches a craft; this one wires the workbench.

## What it ships

| Component | Effect |
|---|---|
| `.mcp.json` | Starts `pf mcp` as the `pf` stdio server. This is what makes `kg_search`, `kg_neighbors`, `kg_path` and `impact_analysis` exist — the tools every project `CLAUDE.md` already tells the agent to call. |
| `commands/` | User-invoked audits (`/security-audit`, `/performance-audit`, `/architecture-review`, `/tech-debt`), shipping (`/ship`, `/blast-radius`), context control (`/context-budget`), and the two external-tool protocols (`/gemini-analyze`, `/ast-grep`). |
| `agents/` | Four verification subagents. They read and report; none of them may write. |
| `hooks/hooks.json` | Formats what the agent edits, injects session context at start, notifies on stop and on permission prompts. |

## Rules

**The MCP server is scoped to one project.** `pf mcp` resolves group/project from
`PF_PROJECT_DIR`, falling back to cwd. In a root session there is no active
project, so warehouse and graph tools return "not inside a project" — that is the
isolation working, not a fault. Use `pf work <group> <project>` to get a session
where they answer.

**Ask the graph before reading files.** `kg_search` costs a few hundred tokens;
reading four models to find the same edge costs thousands and is likelier to be
wrong. `impact_analysis` before changing any column, model or metric.

**The subagents in `agents/` are read-only by construction.** A verifier that can
edit stops being a second opinion and becomes a second author. If one of them
finds a fault, it reports; the main session fixes.

**Formatting is not review.** The PostToolUse hook normalises whitespace and
import order. It does not vouch for the SQL. `/blast-radius` and `pf check` do.

**These commands never cross an entity boundary.** An audit runs against the
active project. If you need the same audit for a sister, open a session there —
carrying a finding across is the bug the gate exists to stop.
