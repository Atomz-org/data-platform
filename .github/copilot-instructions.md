# Copilot instructions

This repository is worked by more than one agent. The rules are written once
and shared; this file only says where they are and what Copilot has to do by
hand that Claude Code's hooks do for it.

1. **Read `CLAUDE.md` first.** It is the router for every agent — what the
   directories are, what is shared, what is read-only, what is recorded.
2. **Then `AGENTS.md`.** The protocol: where you may write, which files are
   generated, what to run before pushing, how to leave a note.
3. **Then `uv run pf memory show`** from wherever you are working. It prints
   the lessons earlier sessions — Claude's or yours — left about exactly that
   scope. The index is `.memory/MEMORY.md`; the notes are `.memory/notes/` at
   the root, under `platform/`, and under each group and project.

What Copilot must do that the Claude Code session layer does automatically:

- **Run the gate before committing.** There is no PreToolUse hook here.
  `uv run pf gate --paths "<comma-separated staged paths>"` is what the
  pre-commit hook runs; `uv run pf install-hook` installs it after `uv sync`.
- **Stay inside one project.** Never read or edit a sister project's files —
  the Claude settings deny it at the tool level; here it is your discipline.
- **Regenerate, never hand-edit.** `kg/architecture.md`, `kg/graph.json`,
  `.github/workflows/<project>.yml`, `platform/tests/README.md`,
  `.memory/MEMORY.md` are all generated. `AGENTS.md` §3 names the command.
- **Leave a note.** Before finishing, `uv run pf memory add <module> <name>
  "<one line>"` for anything non-obvious you learned — a new dependency, a
  constraint you established, a generator that surprised you. Dense and
  keyword-rich, not prose. Commit it with the regenerated index.
- **The maps win.** If what you are asked for contradicts `kg/architecture.md`
  or `docs/ARCHITECTURE.md`, say so; change the code and regenerate the map,
  never the map to match the request. Session state is the branch and the PR,
  not a file — do not create a shared task ledger.

Environment for the coding agent is `.github/workflows/copilot-setup-steps.yml`:
submodules pin by pin, `uv sync --frozen`, the commit gate installed.
