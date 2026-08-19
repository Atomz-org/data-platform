# Contributing

Thanks for your interest in contributing. This repository has a few structural
rules that are stricter than most projects — they exist because the platform is
multi-tenant and its audit trail is part of the product.

## Ground rules

- **`vendor/` is read-only, always.** The 21 upstreams are pinned as submodules
  for provenance; what we adopted from each is recorded in
  `platform/src/pf/vendor/registry.yaml`. Bumping a pin is a maintainer
  decision made through the weekly sync PR, never part of a feature change.
- **Never copy logic between groups or sister projects.** Business logic under
  `groups/<group>/projects/<project>/` belongs to one entity. An assumption
  carried across entities is a bug, not a refactor.
- **Do not edit `provenance/`.** The action record is append-only and written
  by the platform's hooks; `pf provenance verify` blocks CI if the chain is
  broken.
- **`platform/` changes are infrastructure changes.** They affect every group.
  Keep them separate from any change to a specific group or project.

## Getting started

```bash
git clone <your-fork>
cd data-platform
uv sync
uv run pf status        # sanity check: every group and project
```

Submodules are only needed for vendor-drift work: `git submodule update --init`.

## Before you open a pull request

```bash
uv run ruff check .
uv run pytest platform/tests
uv run pf check          # semantic-layer conformance
uv run pf provenance verify
```

CI runs `pf pr report`, which posts a single block/review/clear verdict comment
covering blast radius, path gates, and vendor drift. "Clear" is not approval —
a maintainer still reviews.

## Commit conventions

- Conventional-commit style subjects (`feat(scope): …`, `fix(scope): …`,
  `docs: …`), as in the existing history.
- Sign off your commits (`git commit -s`) to certify the
  [Developer Certificate of Origin](https://developercertificate.org/): you
  wrote the change or otherwise have the right to submit it under this
  repository's license.

## Reporting issues

Use the issue tracker for bugs and feature requests. For anything
security-sensitive, follow [SECURITY.md](SECURITY.md) instead of opening a
public issue.
