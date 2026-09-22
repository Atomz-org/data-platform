# Agents — the protocol every coding agent follows here

For every tool that writes code in this repository — GitHub Copilot, Codex,
Gemini, Cursor, Jules, OpenCode, a local model behind Continue, Claude Code —
and for the people who review what they did. The rules do not depend on which
model you are. They depend on **how you were invoked**: §0 says how to tell,
and everything after it is written per scope, never per vendor.

`CLAUDE.md` is the router — what the directories are, what is shared, what is
read-only, what is recorded — held under a hard 700-token budget so every
session can afford it. **Read it first**, then this file. Nothing here
contradicts it; this adds what a tool without Claude Code's hooks and MCP
server has to do by hand.

| How you got here | Your entry point | Reaches this file |
|---|---|---|
| Codex, Copilot coding agent, Cursor, Jules, OpenCode, Amp | `AGENTS.md`, natively | you are reading it |
| Claude Code — a session, or `@claude` in Actions | `CLAUDE.md` + hooks; the SessionStart hook names this file | on demand |
| Copilot in VS Code — chat, inline | `.github/copilot-instructions.md` | it points here; `chat.useAgentsMdFile: true` reads it directly |
| Gemini CLI, Gemini Code Assist | `GEMINI.md` | imports this file |
| Continue.dev, Ollama, mlx, anything that only takes a system prompt | the operator's prompt | paste this file, or one rule: *follow `AGENTS.md`* |
| Any of the above, for the graph and the gate | `docs/HARNESSES.md` — the generated per-harness configs (`.codex/`, `.cursor/`, `.gemini/`, `.vscode/mcp.json`, `.opencode/`), and what each one actually enforces | it points here |

## 0. Which scope you are in

Decide by what you can do, not by what you are called:

| Scope | You are in it when | For example |
|---|---|---|
| **Session** | a person is in the loop and you have a shell | Claude Code, Gemini CLI, Codex CLI, Copilot chat in agent mode, Cursor agent, Continue agent |
| **Autonomous** | an event started you, no one answers questions, you have a shell | `@claude` in Actions, the Copilot coding agent on an issue, Jules, Codex cloud |
| **Inline** | you see one file and a cursor, and no shell | Copilot completions, Gemini Code Assist inline, Cursor tab, Continue autocomplete |

- **Session** owns design, multi-file change, refactors, and anything that
  needs the graph or `pf`. It runs §1–§5 in full, regenerates the maps, and
  writes the notes.
- **Autonomous** is Session with nobody to ask. Run every check in §4
  yourself; push a branch and describe it — this organisation does not let
  Actions open pull requests, so a person clicks "create"; leave a note (§5),
  because no one else will; and when a map contradicts the request, stop and
  say so in the issue or the PR instead of guessing.
- **Inline** implements what a Session decided. Complete within the file's
  existing patterns and the constraints the maps and notes state. Never add a
  dependency, a model, a column or a generated file from a completion; if the
  completion would need one, leave it to a Session. You cannot write memory:
  hand a lesson to the person as a one-line comment beginning `NOTE(memory):`
  and the Session that commits turns it into a note.

If you cannot tell which you are, you are Inline.

## 1. Before you start — the read protocol

Three kinds of shared state. All of it is generated from, or tracked in, the
repository; none of it is a scratch file. Assimilate it; do not narrate it
back unless asked.

| What | Where | Read it for |
|---|---|---|
| what earlier agents learned | `.memory/MEMORY.md`, the index → `.memory/notes/` at the root, under `platform/`, under each group and each project | the traps that already cost a session; a constraint someone established |
| what the system is | `groups/<g>/projects/<p>/kg/architecture.md` for a project, `docs/ARCHITECTURE.md` for the repo — both projections of `kg/graph.json` | models, columns, metrics, dependencies: ask before changing any of them |
| what the engine's code does | the code graph over `platform/` — `pf code impact <file>`, `pf code search <name>`, or its MCP tools | callers, dependents and covering tests of a platform file, before you change it |
| what has been decided | `docs/POLICY.md`, `decisions/`, the project's `CLAUDE.md` | standing rules a person reviewed; business rules the graph cannot encode |

With a shell:

```bash
uv sync --frozen
uv run pf install-hook          # the commit gate; git does not clone .git/hooks
uv run pf memory show           # what applies where you are, one line each; --full for bodies
```

Without one, read the index and then the notes for your module; the index is
one line per note and links to each.

**Ask the right graph.** Two exist and they do not overlap. Models, columns,
metrics, sources, exposures and lineage are the *data* graph: `pf kg`, and the
`kg_search` / `kg_neighbors` / `impact_analysis` MCP tools. Which Python
function calls which is the *code* graph: `pf code`, scoped to `platform/`
because that is the only module with no sisters. Neither answers the other's
question, and reading files to work out either is the thing both exist to
stop.

Visibility is the same for every tool: root and `platform/` always, your
group and your project when you are inside one, **never a sister project**.
That is the denylist `.claude/settings.json` enforces for Claude at the tool
level. Everywhere else it is your discipline. The code graph obeys it by
construction: its root is `platform/`, fixed by a tracked marker directory,
so a sister's code is not reachable from it at all.

## 2. Where you may write

| Scope of the change | You may change | You may not |
|---|---|---|
| a project | `groups/<g>/projects/<p>/**` | any other project, `platform/**`, `vendor/**` |
| a group | its `groups/<g>/**` | a sister group |
| platform | `platform/**`, root docs, `.github/**` | `vendor/**`, `provenance/**` |

`vendor/` is read-only always; bumping or adding a pin is a human decision.
`provenance/**` is the record of what agents did — denied to every agent.
`gate.yaml` is the machine-readable version of this table and the pre-commit
hook enforces it. Only Claude Code has a hook that checks paths before an edit
lands; every other tool **runs the gate itself before committing**:

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
| `docs/ONBOARDING.md`, `docs/onboarding.html` | `pf guide build` | the repository, or `pf/guide.py` |
| `platform/tests/README.md` | `pf test index` | the test docstrings |
| `.memory/MEMORY.md` | `pf memory index` (or `pf memory add`) | the notes |
| `docs/VENDOR*.md` | `pf vendor docs` | `platform/src/pf/vendor/registry.yaml` |
| `.codex/`, `.cursor/`, `.gemini/`, `.vscode/mcp.json`, `.opencode/`, `docs/HARNESSES.md` | `pf context refresh` | `.mcp.json` for the servers; `platform/src/pf/harness.py` for the rest |

`pf context refresh` regenerates the memory index, the test index, the
repo map, the onboarding guide and the harness configs in one step — the fix the `agent-context` workflow names when a pull
request leaves any of them stale.

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
uv run pf guide check                             # onboarding guide current
uv run pf context check                           # entry points still agree; every module has its README
uv run pytest platform/tests -q                   # the platform suite
uv run pf kg build <g> <p> && uv run pf arch <g> <p> --check   # any project change
uv run pf kg check <g> <p> --strict
uv run pf tokens                                  # touched a CLAUDE.md or a card
```

Commits: **at most 12 files each** (`gate.yaml` `maxFiles`), a subject line
that says what changed and a body that says why, never `--no-verify`. Split
larger work into a sequence — the history is full of `(1 of 2)`.

**A feature lands with its evidence.** `gate.yaml`'s `tests_required` refuses
a run that adds a file under `platform/src/pf/` or `platform/hooks/` with
nothing under `platform/tests/`, or a skill under a toolkit with nothing under
that toolkit's `evals/`; a run that only modifies one is warned. So the test
travels in the same commit as the code, not the next one — split by feature,
not by kind. Deleted tests are never shown to the gate, so removing one is
not evidence. What the gate cannot judge is yours to: the evidence must fail
before the change and pass after it, and the rest of this section must still
be green — new behaviour never buys itself room by weakening an existing
check.

## 5. Before you finish — the write protocol

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

The note records **who** wrote it, and will not be written without: `--agent
<name>` if you say, otherwise detected from your environment — `PF_AGENT`,
else Claude Code's `CLAUDECODE`, Gemini CLI's `GEMINI_CLI`, GitHub Actions'
actor, else a person at a keyboard as `human`. A tool the detector does not
know exports `PF_AGENT=<name>` once and nothing else changes. The index shows
it as a column; `pf memory show --toon` prints
`notes[N]{module,name,type,status,agent,description}`, which is the form the
SessionStart hook injects.

A hand-off is not a separate ledger. Every field of one is already recorded:

| Hand-off field | Where it lives |
|---|---|
| who | `agent:` on the note; the commit author |
| when | `git log` — `pf memory log` |
| task | the branch and its pull request |
| state | `status: active` or `resolved` on the note; the PR's state |
| files modified | the commit |
| new constraint | a note of type `feedback` (a rule) or `project` (a fact), in the module it constrains |

Write notes dense, not conversational: the one line is keyword-rich
(`pf kg build reads target/manifest.json; never reparses on model change`),
the body is why + how-to-apply, nothing else — `stack: [dlt, dbt, DuckDB]`
beats a paragraph.

## 6. Source of truth, dependencies, and session state

**The repository is the source of truth; the maps are projections of it.**
`kg/graph.json`, `kg/architecture.md`, `docs/ARCHITECTURE.md` and
`.memory/MEMORY.md` are generated from the code and checked against it in
CI. If a request contradicts what a map says, say so before acting — and
resolve it by changing the code and regenerating, never by editing the map to
match the request. A hand-written architecture file the tools do not generate
is not a source of truth here; it is a second opinion that drifts.

**A new dependency, library or pattern is a decision, and decisions are
recorded.** Add it where it lives (`pyproject.toml`, a capability, a toolkit)
*and* leave a memory note in the module it constrains, saying what it rules
out. `docs/POLICY.md` and `decisions/` are where standing constraints go once
a person has reviewed them.

**Session state lives in git, not in a file.** What is in progress is the
branch and its pull request; what an agent did is the provenance chain
(`pf provenance`); what a loop found is `STATE.md`. Several agents, of several
tools, work this checkout at once; one mutable file every session appends to
is a conflict on every PR, and a second copy of the architecture is stale on
the first commit after it is written.

**Every pull request is checked for all of this.** The `agent-context`
workflow runs on every PR, with no path filter: the entry points must agree
(`pf context check`), and the memory index, the test index, the repo map and
the onboarding guide must be current. When they are not, the run summary shows what
`pf context refresh` would change; with an `AGENT_CONTEXT_TOKEN` secret the
workflow commits that refresh to the branch itself.

## 7. Never

- Read another group or another sister project. Business logic does not
  transfer between entities; an assumption carried across is a bug.
- Write under `vendor/` or `provenance/`, or commit anything matching
  `gate.yaml`'s `denylist` (secrets, warehouses, build output).
- Create a parallel memory or state directory — an `.agent-memory/`, a
  `session_state` file, a hand-written architecture graph. §1 lists where
  each of those already lives, generated and checked.
- Run `pf loop run-all` as a side effect of anything — it is real agent
  execution against warehouses, not a report.
- Expand `CLAUDE.md`. It is budgeted and CI-enforced; new material goes in
  `docs/` or in a memory note.
- Land a feature without the test or eval that proves it, or make the
  suite green by deleting or loosening an existing check. The gate refuses
  the first (§4, `tests_required`); review is the guard for the second.
