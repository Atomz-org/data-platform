# `tests` — does the shared code still work?

**Workflow:** `.github/workflows/platform.yml` · **Job:** `tests`
**Sibling:** `suite` in `platform-tests.yml` runs the *identical* command.

## In one paragraph

Every company in this repo runs on the same shared engines in `platform/`.
Each company's own workflow only tests that company. So before this job
existed, the shared code — the gates, the scaffolder, the graph — was tested by
nothing. This job installs Python and runs **1,488 pytest cases**, then lints.

## When it runs

Pull requests only, and only when one of six paths changes:

```
platform/**   pyproject.toml   uv.lock   gate.yaml
groups/*/group.yaml   .github/workflows/platform.yml
```

Note what is **not** there: `groups/*/projects/**`. Editing one company's dbt
models never wakes this job.

## What actually fails

| Step | Fails when |
|---|---|
| `uv sync` | `uv.lock` disagrees with `pyproject.toml`. You added a dependency and forgot `uv lock`. |
| `uv run pytest platform/tests -q` | Any test fails — see the three kinds below |
| `uv run ruff check platform` | Any lint rule fires; usually `I001`, unsorted imports |
| Vendored upstreams | **Never.** Failures become a `::warning`; the step always exits 0 |

### The three kinds of test failure, most common first

**1. A generated file is committed stale.** The suite regenerates it from
source and compares byte for byte. This is the most common failure and it is
usually in a file you did not touch.

**2. A structural rule about the suite is broken.** A test file sitting
directly in `platform/tests/` instead of a named group; a test file with no
module docstring; a test file on disk but never `git add`ed.

**3. An ordinary logic regression** — a normal pytest traceback.

## Worked example — the one everyone hits

You fix a bug and add a regression test at
`platform/tests/gate/test_my_rule.py`. It passes locally. You commit both files
and push.

CI fails in a file you never opened:

```
FAILED platform/tests/gate/test_suite_index.py::test_the_committed_index_matches_the_suite
AssertionError: assert 'platform/tests/README.md is stale; run `pf test index`' == ''
```

**Why.** `platform/tests/README.md` is a generated index of the suite — "63
files · 1065 test functions". Adding a test file changes those numbers, so the
committed index no longer matches what it describes.

**Fix:**

```bash
uv run pf test index                  # rewrites platform/tests/README.md
git add platform/tests/README.md
git commit --amend --no-edit
```

This happened on this very branch. Twice.

## A real one from this branch

Lint caught four `I001` errors in three test files added for the scratch-link
work. `pf` lives at `platform/src/pf`, so ruff classifies it as **third-party**
— `from pf import workflows` must sit in the same block as `import pytest`,
with no blank line between:

```python
import pytest
from pf import workflows as w      # same block, no blank line
```

There is no `--fix` in CI. Locally:

```bash
uv run ruff check platform --fix
```

## Reproduce the whole job locally

```bash
uv sync
uv run pytest platform/tests -q       # NOT platform/tests/gate — CI runs the whole tree
uv run ruff check platform
```

> **Run the whole tree.** Running one sub-directory and reporting it green is a
> mistake this repo has already paid for: a change to `link()` broke five tests
> in `platform/tests/capabilities/` while `platform/tests/gate/` stayed green.
