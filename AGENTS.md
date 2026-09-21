# Agents — the protocol every coding agent follows here

For GitHub Copilot's coding agent, Codex, and any other tool that reads
`AGENTS.md`. Claude Code reads `CLAUDE.md`, which is the canonical router for
this repository and is kept under a hard 700-token budget — **read it first**,
then this file. Nothing here contradicts it; this file adds what a tool
without Claude Code's hooks and MCP server has to do by hand.

## 1. Before you start

```bash
uv sync --frozen
uv run pf install-hook          # the commit gate; git does not clone .git/hooks
uv run pf memory show           # what earlier sessions learned about where you are
```

**Memory is shared and lives in the repo**, not in any one tool's private
store. `.memory/notes/` exists at the root, under `platform/`, under every
`groups/<g>/` and every `groups/<g>/projects/<p>/`; `.memory/MEMORY.md` is
the generated index of all of them. `pf memory show` prints the notes visible
from your working directory — root and platform always, the group and project
when you are inside one, **never a sister project**. Read them before touching
anything they describe; they are the traps that already cost a session.

## 2. Where you may write

| Scope | You may change | You may not |
|---|---|---|
| a project | `groups/<g>/projects/<p>/**` | any other project, `platform/**`, `vendor/**` |
| a group | its `groups/<g>/**` | a sister group |
| platform | `platform/**`, root docs, `.github/**` | `vendor/**`, `provenance/**` |

`vendor/` is read-only always; bumping or adding a pin is a human decision.
`provenance/**` is the record of what agents did — denied to every agent.
`gate.yaml` is the machine-readable version of this table and the pre-commit
hook enforces it; Copilot has no PreToolUse hook, so **run the gate yourself
before committing**:

```bash
uv run pf gate --paths "$(git diff --cached --name-only | tr '\n' ',')"
```

## 3. Generated files: change the generator, not the file

Much of this tree is generated *and* committed so it can be diffed in review.
Hand-editing one is silently discarded by the next regeneration.

| Artefact | Regenerate with | Change instead |
|---|---|---|
| `.github/workflows/<project>.yml` | `pf bootstrap <g> <p>` | the capability's `ci_jobs` |
| `**/kg/architecture.md` | `pf kg build <g> <p>` then `pf arch <g> <p>` | the project |
| `**/kg/graph.json` | `pf kg build <g> <p>` | the project |
| `docs/ARCHITECTURE.md` | `pf arch build` | the repository |
| `platform/tests/README.md` | `pf test index` | the test docstrings |
| `.memory/MEMORY.md` | `pf memory index` (or `pf memory add`) | the notes |
| `docs/VENDOR*.md` | `pf vendor docs` | `platform/src/pf/vendor/registry.yaml` |

A regenerated artefact is safe to commit only when the generator could see
everything the committed copy was built from. Without a warehouse, `pf kg
build` silently drops typed column nodes; without a fresh
`transform/target/manifest.json` it reads days-old dbt state; without `vendor/`
the schema-derived files change shape. Reproduce the CI job's own order and
compare node *sets*, not diff line counts. `platform/.memory/notes/` records
each of these traps in detail.

## 4. Before you push

What CI runs, in order. Run the ones your change reaches:

```bash
uv run ruff check platform/                       # any platform/** change
uv run pf test check                              # added or moved a test file → pf test index
uv run pf memory check                            # added or edited a note   → pf memory index
uv run pf arch check                              # repo map current
uv run pytest platform/tests -q                   # the platform suite
uv run pf kg build <g> <p> && uv run pf arch <g> <p> --check   # any project change
uv run pf kg check <g> <p> --strict
uv run pf tokens                                  # touched a CLAUDE.md or a card
```

Commits: **at most 12 files each** (`gate.yaml` `maxFiles`), a subject line
that says what changed and a body that says why, never `--no-verify`. Split
larger work into a sequence — the history is full of `(1 of 2)`.

## 5. Before you finish

If you learned something the next agent would otherwise pay for again — a
command that only works in one order, a generator that degrades silently, a
count that means something other than it looks — write it down where it
belongs and let the index follow:

```bash
uv run pf memory add <module> <kebab-name> "<one line>" --body-file notes.md
```

`<module>` is `root`, `platform`, `groups/<g>` or `groups/<g>/projects/<p>`:
the narrowest scope the lesson is true of. Commit the note and the regenerated
`.memory/MEMORY.md` together. Do not hand-edit the index.

Write notes dense, not conversational: the one line is keyword-rich
(`pf kg build reads target/manifest.json; never reparses on model change`),
the body is why + how-to-apply, nothing else. `pf memory show --toon` prints
the visible notes as TOON rows (`notes[N]{module,name,type,status,description}`),
which is the form the SessionStart hook injects.

## 6. Source of truth, dependencies, and who does what

**The repository is the source of truth; the maps are projections of it.**
`kg/graph.json`, `kg/architecture.md`, `docs/ARCHITECTURE.md` and
`.memory/MEMORY.md` are generated from the code and checked against it in
CI. If a request contradicts what a map says, say so before acting — and
resolve it by changing the code and regenerating, never by editing the map to
match the request. A hand-written architecture file that the tools do not
generate is not a source of truth here; it is a second opinion that drifts.

**A new dependency, library or pattern is a decision, and decisions are
recorded.** Add it where it lives (`pyproject.toml`, a capability, a toolkit)
*and* leave a memory note in the module it constrains, saying what it rules
out. `docs/POLICY.md` and `decisions/` are where standing constraints go once
a person has reviewed them.

**Session state lives in git, not in a file.** What is in progress is the
branch and its pull request; what an agent did is the provenance chain
(`pf provenance`); what a loop found is `STATE.md`. Do not add a shared
"current tasks" file — several agents work this checkout at once, and one
mutable file every session appends to is a conflict on every PR.

**Who does what:** any agent may take any task inside its scope, and the
gates are the same for all of them. In practice —

| Agent | Typically | Gets its rules from |
|---|---|---|
| Claude Code (session) | scaffolding, multi-file refactors, anything needing the graph or `pf` | `CLAUDE.md` + hooks + MCP, automatically |
| `@claude` (Actions) | an issue or comment asking for an implementation | the same, via `.github/workflows/claude.yml` |
| Copilot coding agent | an issue assigned to it; a scoped feature or fix | this file + `.github/copilot-instructions.md` + `copilot-setup-steps.yml` |
| Copilot inline | completions inside a file someone is editing | `.github/copilot-instructions.md`; treats `.memory/` and the maps as read-only context |

## 7. Never

- Read another group or another sister project. Business logic does not
  transfer between entities; an assumption carried across is a bug.
- Write under `vendor/` or `provenance/`, or commit anything matching
  `gate.yaml`'s `denylist` (secrets, warehouses, build output).
- Run `pf loop run-all` as a side effect of anything — it is real agent
  execution against warehouses, not a report.
- Expand `CLAUDE.md`. It is budgeted and CI-enforced; new material goes in
  `docs/` or in a memory note.
