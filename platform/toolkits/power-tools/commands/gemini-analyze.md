---
name: gemini-analyze
description: Hand a repo-sized question to Gemini's large context window instead of compacting this session. Read-only analysis.
disable-model-invocation: "yes"
---

# Large-context analysis with the Gemini CLI

When a question needs more files than this session should hold, shell out to
`gemini -p` rather than reading everything in. Ported from the source guide;
`gemini` is installed on this machine, so it works as written.

Question: `$ARGUMENTS`.

## Scope rule for this repo — read first

Run `gemini` **from the active project directory**, and never pass `@` paths that
reach into another group or sister project. `--all_files` from the repo root
would sweep every entity in the monorepo, which is exactly the cross-entity read
the gate exists to prevent. It also drags `vendor/` (fourteen upstreams) and
`.venv` into the prompt.

Safe:

```bash
cd groups/<group>/projects/<project>
gemini -p "@transform/models/ @src/ Where does customer status get derived, and by which model?"
```

Not safe: `gemini --all_files -p …` from the repo root.

For a platform-wide question, scope it to shared infra only:

```bash
gemini -p "@platform/src/pf/ Summarise how the gate, the graph and the MCP server relate"
```

## Syntax

`@` includes files and directories, resolved relative to the directory you run
`gemini` in.

```bash
gemini -p "@transform/models/marts/ Summarise the grain of each mart"
gemini -p "@src/ @transform/ Which sources feed which marts?"
gemini -p "@transform/models/ Is there any model that selects straight from a source?"
```

## When to reach for it

- the file set exceeds what this session should carry (roughly >100 KB),
- a whole-project sweep: "is X implemented anywhere", "list every place Y appears",
- comparing many large files at once,
- verifying a *negative* — "nothing in this project references a sister" — where
  missing one file makes the answer wrong.

## When not to

- **Anything the knowledge graph already answers.** `kg_search`, `kg_neighbors`,
  `kg_path` and `impact_analysis` are cheaper, faster and structurally correct.
  Gemini reads text; the graph knows the edges. Use the graph first, and reach
  for Gemini only when the question is not a graph question.
- Anything that needs to write. This is read-only analysis; no `--yolo`.
- Anything touching secrets — `@` inlines file contents into a third-party
  request. Never include `.env`, `.dlt/secrets.toml`, or `credentials/`.

## After

Treat the output as a lead, not a finding. Verify each claim against the file it
names before acting on it, and cite `path:line` in your own report.
