# Developing on this platform

Commands, generated-file discipline and the commit gate — the detail that
doesn't fit `CLAUDE.md`, which is budgeted at 700 tokens (`ROUTER_BUDGET` in
`platform/src/pf/kg/card.py`) because it is loaded by every session. This is
the page it would have been if that constraint didn't exist.

## Commands

```bash
uv sync                                   # install
uv run pf install-hook                    # REQUIRED on a fresh clone
```

`install-hook` is not optional. Git does not clone `.git/hooks`, so until it
runs, the pre-commit gate that refuses a hand-edited generated artefact is
simply absent and nothing says so.

What `.github/workflows/platform-tests.yml` runs, in order — run these before
pushing a `platform/**` change, because that workflow is the only repo-wide
gate:

```bash
uv run ruff check platform/               # lint
uv run pf test check                      # is platform/tests/README.md current?
uv run pf arch check                      # is docs/ARCHITECTURE.md current?
uv run pytest platform/tests -q           # the platform suite
```

Narrowing the suite — each directory under `platform/tests` names the part of
the platform it guards (`capabilities`, `gate`, `graph`, `onboarding`,
`ontology`):

```bash
uv run pytest platform/tests/gate                              # one area
uv run pytest platform/tests/gate/test_suite_index.py          # one file
uv run pytest platform/tests/gate/test_suite_index.py::test_x  # one test
uv run pf test where <subject>            # which tests cover this?
```

**Adding a test file means regenerating the index.** `pf test check` fails the
build when `platform/tests/README.md` and the suite disagree; run
`uv run pf test index`.

Formatting is not in CI, so it will not tell you: `just fmt` (ruff format plus
import order over `platform` and `groups`), `just fmt-sql <g> <p>` (sqlfluff
over one project's models). Every `just` recipe is a one-line `pf` delegate —
read the `justfile` rather than guessing a flag.

## Generated files: change the generator, not the file

Much of this tree is generated and committed. The two are not in conflict — a
generated artefact is committed so it can be *diffed in review*, not so it can
be edited. `gate.yaml`'s `denylist` refuses the edit; `denylist_except` is what
lets git carry the file anyway, and the comments there explain each decision.

Hand-editing one of these is silently discarded by the next regeneration:

| Artefact | Regenerate with | Change instead |
|---|---|---|
| `.github/workflows/<project>.yml` | `pf bootstrap <g> <p>` | the capability's `ci_jobs` |
| `.github/workflows/platform.yml` | `pf bootstrap` | `PLATFORM_WORKFLOW` in `pf/scaffold/bootstrap.py` |
| `**/kg/architecture.md` | `pf arch <g> <p>` / `--all` | the project, or the feature registry |
| `**/kg/graph.json` | `pf kg build <g> <p>` | the project |
| `docs/ARCHITECTURE.md` | `pf arch build` | the repository, or `pf/archmap.py` |
| `docs/ONBOARDING.md`, `docs/onboarding.html` | `pf guide build` | the repository, or `pf/guide.py` |
| `**/HARNESS.md` — a group's, a project's, its `reporting/`'s | `pf harness <g> [<p>]` / `build` | the settings, gate, hooks, workflow, loops and tools it is read from, or `pf/harnessmap.py` |
| `platform/tests/README.md` | `pf test index` | the test docstrings |
| `docs/VENDOR-CARD.md`, `docs/VENDOR.md` | `pf vendor docs` | `pf/vendor/registry.yaml` |
| `gate.capabilities.yaml` | `pf bootstrap` | the capability |

Post-scaffold work is **one** ordered idempotent list — `pf.scaffold.bootstrap.STEPS`.
A new platform capability is a step there, and `pf bootstrap --all` retrofits
every existing project. `pf bootstrap-steps` prints what runs and why.

`pf arch check` (repository) and `pf arch <g> <p> --check` (one project) are
different gates with near-identical names. CI runs both.

`STATE.md` is a different kind of generated file from everything above: it is
rewritten only by *running* loops (`pf loop run-all <g> <p>`), which is real
agent execution — pipelines, possibly PRs — not a report over the repository's
current shape. `pf loop audit` is the read-only version; it scores readiness
without touching `STATE.md`.

## Verifying a regenerated artefact

**A regenerated artefact is only safe to commit when the generator could see
everything the committed copy was built from.** This tree's generators degrade
silently rather than failing when an input is absent:

- No warehouse → `pf kg build` drops `Column` nodes that carry real
  `data_type` values. Rebuilding a graph whose committed copy was built against
  a live warehouse *deletes thousands of nodes*.
- No `vendor/` submodules → the generators that read vendored JSON schemas
  (`otop.json`, `openmetadata.json`, `mdl.json`) and `pf air coverage` produce
  different or empty output.
- No graph → `pf arch --check` renders `✓` where it should render `✓ n`, so a
  fresh checkout reports rows as changed that CI does not, and a warm tree
  reports a pass CI does not.
- **A stale dbt manifest** → `pf kg build` reads `transform/target/manifest.json`
  for models, columns, tests and exposures. `ensure_manifest` (in
  `pf.runtime.dbt_runtime`) only reparses when the manifest is *absent* or
  `dbt_packages/` is missing a declared package — never because a model file
  changed underneath it. `target/` is gitignored, so a long-lived local
  checkout can hold a manifest from days before the models it is meant to
  describe, and every downstream read is confidently wrong in whichever
  direction the stale manifest happens to point. If a project's map looks
  stale in a way that contradicts what CI just said, delete
  `transform/target/manifest.json` and rebuild before trusting the local
  result.

So: **reproduce the job's own order**, and diff node sets rather than lines.
Every per-project workflow builds the graph before checking the map:

```bash
rm -f groups/<g>/projects/<p>/transform/target/manifest.json  # force a reparse
uv run pf kg build <g> <p> && uv run pf arch <g> <p> --check
```

Line counts are not evidence. Node order in `graph.json` is unstable, so a
16-node addition can render as a 7,500-line diff — large enough to hide a
deletion completely. Compare the sets:

```bash
python3 -c "import json;print(len(json.load(open('.../kg/graph.json'))['nodes']))"
```

Work in a full `git clone -s <repo>`, not a `git worktree`. `pf install-hook`
does `mkdir` on `.git/hooks`, and in a worktree `.git` is a file, so it raises
`NotADirectoryError`.

## The commit gate

`gate.yaml` is the machine-readable policy, read by `pf gate`, the pre-commit
hook and the PreToolUse hook. Three things to know before staging:

- **`maxFiles: 12`** per commit. Split the work; the repo's own history is
  sequences like `(1 of 2)`.
- **`platform_denylist`** — a *project* session may not write `platform/**`,
  `vendor/**`, `pyproject.toml`, `uv.lock` or the gate files.
- **`impact_required`** — changing model, macro or source files means the blast
  radius must be reported first. `pf impact <g> <p> <node>`, or
  `pf gate --paths` over what you staged.

Deletions are not shown to the gate: `platform/hooks/pre_commit.sh` selects
`--diff-filter=ACMR`, deliberately and with the reasoning recorded in
`gate.yaml`. A delete-only commit passes every rule above unexamined.

## Known gap: a vendor pin the registry describes but never adds

`platform/src/pf/vendor/registry.yaml` carries a full entry for `floci` (id
`floci`, adopted/declined paths, the reasoning for both) but `.gitmodules` has
never had a `vendor/floci` submodule — `git log -S'vendor/floci' -- .gitmodules`
is empty across the repository's whole history. `pf vendor list` and `pf
vendor verify` both correctly report it `missing`. Adding the submodule is a
vendoring decision — the same one `CLAUDE.md` already reserves for a human —
so this is flagged here rather than fixed.
