# Copilot instructions

The rules are written once, for every agent, in `AGENTS.md`. This file only
says where they are and which scope you are in. Read, in order:

1. `CLAUDE.md` — the router: the directories, what is shared, what is
   read-only, what is recorded.
2. `AGENTS.md` — the protocol. §0 tells you your scope; the rest is per scope.
3. `.memory/MEMORY.md` — what earlier agents, of any tool, learned. With a
   shell, `uv run pf memory show` from where you are working prints exactly
   the notes that apply there.

Your scope, in Copilot's terms:

- **Completions and inline chat → Inline.** One file, no shell. Follow the
  file's own patterns and what `kg/architecture.md` and the notes say. Never
  add a dependency, a model, a column or a generated file from a completion.
  A lesson you cannot write goes in a one-line `NOTE(memory):` comment for
  the person to turn into a note.
- **Chat in agent mode → Session.** You have a shell and a person. There is
  no PreToolUse hook here, so run the gate yourself before committing:
  `uv run pf gate --paths "$(git diff --cached --name-only | tr '\n' ',')"`.
- **The coding agent on an issue → Autonomous.** No one answers. Run every
  check in `AGENTS.md` §4, push the branch and describe it, leave a note
  (§5). Your environment is `.github/workflows/copilot-setup-steps.yml`.

The same in all three: stay inside one project — never read a sister; Claude's
settings deny it at the tool level, here it is yours to keep. Regenerate
generated files instead of editing them (`AGENTS.md` §3). When a request
contradicts a map, say so, then change the code and regenerate — never the
map. Session state is the branch and the PR, not a file.

VS Code reads `AGENTS.md` directly when `chat.useAgentsMdFile` is on.
