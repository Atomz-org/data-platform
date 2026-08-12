# ADR-0001 — Platform cleaning macros load via `macro-paths`, not as a dbt package

**Status:** accepted · **Date:** 2026-08-12

## Context

`pf gen-staging` renders staging SQL that calls the shared cleaning macros
unqualified — `{{ pf_clean('id', 'natural_key') }}`, `{{ pf_dedupe('payment_id') }}`.
`pf_clean` then dispatches to its siblings (`clean_natural_key`, `clean_email`, …)
unqualified as well.

`transform/packages.yml` installs `platform/dbt` as a local dbt package named `pf`.
dbt parses it — the macros land in the manifest as `macro.pf.pf_clean` — but dbt
**namespaces macros by package**. From a root-project model, `pf_clean` is undefined,
and the qualified form `pf.pf_clean(...)` fails one level deeper because the inner
dispatch to `clean_natural_key` is itself unqualified.

The generator lives in `platform/` and is shared by every project, so changing what
it emits is not a per-company decision.

## Decision

Add the platform macro directory to this project's root `macro-paths`:

```yaml
macro-paths: ["macros", "../../../../../platform/dbt/macros"]
```

The macros are then compiled as root-project (`acme_us`) macros, so both the
generated call sites and `pf_clean`'s internal dispatch resolve.

The `local:` entry in `packages.yml` is left in place — it is harmless (dbt keeps the
`pf`-namespaced copies alongside), and removing it would churn `package-lock.yml` for
no gain.

## Consequences

- Staging models compile without editing anything under `platform/`.
- The macro path is relative and depends on this project sitting at
  `groups/<group>/projects/<project>/`. A move breaks it loudly at parse time.
- Same macro name in two namespaces (`acme_us` and `pf`). Unqualified calls resolve
  to the root copy; both are the same file on disk via the `dbt_packages/pf` symlink,
  so they cannot drift.
- If the platform later emits `pf.`-qualified calls *and* qualifies the internal
  dispatch, this line should be removed and the package wiring relied on instead.
