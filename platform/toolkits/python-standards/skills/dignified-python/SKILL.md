---
name: dignified-python
description: Production Python conventions for this repo.
---
<!-- Adapted from dagster-io/skills dignified-python (vendor/dagster-skills, Apache-2.0) — see registry.yaml. -->
# Python standards

- Target 3.11–3.12. Contemporary typing: `list[str]`, `str | None`, `Protocol`,
  `@dataclass(frozen=True)` for value objects.
- LBYL over blanket `except`. Catch the specific exception; never `except Exception: pass`
  outside a documented best-effort path.
- `pathlib` everywhere; no `os.path` string joins.
- Lazy-import heavy optional deps (`dlt`, `dagster`, `dbt`) inside functions so the
  platform core works without them installed.
- Public functions get a docstring with an Args section when arguments are not obvious.
- No comment that restates the next line. Comment a constraint the code cannot show.
- Match the surrounding file's idiom and comment density rather than importing a
  house style into it.
