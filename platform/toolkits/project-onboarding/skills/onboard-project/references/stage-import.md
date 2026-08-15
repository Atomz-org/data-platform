# Stage 1 — import

**Goal condition:** the repository is here, every model name is unique, and no
dbt built-in is overridden.

## Evaluate

```bash
pf onboard <group> <project> <git-url-or-path>      # plans, writes nothing
pf align evaluate <group> <project> --stage import
```

`pf onboard` surveys the source and reports what would happen. Read the layer
mapping line before anything else — it says where each incoming directory landed,
and a wrong guess there is expensive to unwind after the metrics stage.

## Implement

```bash
pf new-group <group> --domain ecommerce      # if the group does not exist
pf onboard <group> <project> <source> --apply
```

A new group asserts three things: a shared ontology instance, conformed
dimensions, and a roll-up that means something. If the incoming project shares
none of those with an existing group, it is its own group. Folding an unrelated
company into an existing family to save a directory is how conformed dimensions
stop conforming.

`--force` applies over blocking findings. Use it **only** for findings that are
themselves the work of a later stage — dialect findings are the obvious case,
since the SQL cannot be fixed before it is in the repository. Never use it for
`name-collision` or `reserved-macro`; those produce a project that will not
compile at all.

### What the import deliberately does not carry

| Left behind | Why |
|---|---|
| `profiles.yml` | the platform owns targets; yours is generated |
| `generate_schema_name` and other dbt built-ins | they decide where models land, and this platform's layer separation depends on the default |
| source `test-paths`, `seed-paths`, … | contents are copied into this layout; carrying the keys would name directories the files moved out of |
| `target/`, `target-base/`, `dbt_packages/` | build artefacts; a checked-in manifest is read as current and is not |
| unpinned **and** unused packages | a moving branch that buys nothing |

## Validate

```bash
pf align validate <group> <project> --stage import
```

Four conditions: the project exists, models were imported, model names are
unique, and no dbt built-in is overridden.

**Name collisions.** dbt resolves models by bare name regardless of directory, so
two `orders.sql` anywhere in the tree is fatal. Rename the one whose layer is
less central and record why in `decisions/`.

**Reserved macros.** These are reported, never copied. `generate_schema_name` is
the common one: the usual override collapses every schema into one on non-prod
targets, which silently defeats the `staging`/`marts` separation the knowledge
graph and the impact gate both read.

## Then

`pf align status` — the ontology stage is next, and it needs the annotations that
nothing has written yet.
