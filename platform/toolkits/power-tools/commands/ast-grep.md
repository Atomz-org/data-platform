---
name: ast-grep
description: Structural, syntax-aware code search and rewriting with ast-grep, for when regex would match the wrong thing.
---

# Structural search with ast-grep

Ported from the source guide. Use instead of plain text search when the pattern
is **structural** rather than textual.

Pattern / task: `$ARGUMENTS`.

## Availability — check before promising results

`ast-grep` is **not installed** in this environment as of writing:

```bash
command -v ast-grep >/dev/null 2>&1 || echo "ast-grep not installed"
# install: brew install ast-grep   (or: cargo install ast-grep --locked)
```

If it is absent, say so once and fall back to Grep with a pattern narrowed by
path and file type. Do not silently degrade — a structural question answered
textually gives a different, usually longer, answer.

## When it is the right tool

- structural patterns: every call site of a function, every class definition,
  every decorator usage,
- language-aware refactors: renaming a symbol, changing a signature, rewriting
  imports — where regex would also hit strings, comments and unrelated names,
- finding a pattern across several syntactic contexts at once,
- cross-language sweeps in this monorepo (Python pipelines, TypeScript in
  `platform/src/pf/ui/web`, YAML config).

## Syntax

```sh
ast-grep --pattern '$PATTERN' --lang $LANGUAGE $PATH
```

| Token | Meaning |
|---|---|
| `$VAR` | matches one node, captures it |
| `$$$` | matches zero or more nodes |
| `$$` | matches one or more nodes |
| literal code | matches exactly |

Languages: python, typescript, javascript, go, rust, java, c, cpp, html, css,
yaml, json, and more.

## Patterns that pay off in this repo

```sh
# every annotated dlt resource
ast-grep --pattern '@annotate($$$)' --lang python groups/<g>/projects/<p>/src/

# every dlt resource declaration, annotated or not — the diff is the debt
ast-grep --pattern '@dlt.resource($$$)' --lang python groups/<g>/projects/<p>/src/

# direct warehouse construction outside the runtime factory
ast-grep --pattern 'Warehouse($$$)' --lang python .

# React hooks in the control-plane UI
ast-grep --pattern 'const [$S, $SET] = useState($$$)' --lang typescript platform/src/pf/ui/web/
```

Scope every invocation to one project or to `platform/`. A bare `.` from the repo
root walks `vendor/` (fourteen submodules) and `.venv`, and crosses entity
boundaries.

## Advanced

```sh
ast-grep --pattern '$P' --lang $LANG $PATH --json        # machine-readable
ast-grep --pattern '$OLD' --rewrite '$NEW' --lang $LANG $PATH
```

Rewrites go through the same gate as any other edit — check `/blast-radius`
before rewriting anything the graph knows about, and never rewrite under
`vendor/`, which is read-only always.

## Tool choice

| Task | Tool |
|---|---|
| find a literal string | Grep |
| find a code structure | ast-grep |
| find what depends on what | `kg_neighbors` / `impact_analysis` |
| understand a concept's meaning | `kg_search`, the ontology |
| precise edits | Edit, after the search |

The graph outranks both search tools for dependency questions: it knows edges
that no amount of syntax matching will recover.
