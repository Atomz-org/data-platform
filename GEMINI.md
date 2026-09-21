# Gemini — the shared protocol

This repository's rules are written once, for every agent. `CLAUDE.md` is the
router; `AGENTS.md` is the protocol, and its §0 tells you which execution
scope you are in — Session (Gemini CLI), Autonomous (Jules), Inline (Code
Assist completions). Memory shared by every tool is `.memory/MEMORY.md`; with
a shell, `uv run pf memory show` prints what applies where you are, and
`uv run pf memory add` records a lesson under your own name (`GEMINI_CLI` is
detected; otherwise `export PF_AGENT=<name>`).

Both files follow, imported so they load with this one:

@./CLAUDE.md

@./AGENTS.md
