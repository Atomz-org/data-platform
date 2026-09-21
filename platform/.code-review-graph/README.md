# Code graph marker

This directory makes `platform/` the root of the code graph, and that is its
whole job. `code-review-graph` resolves `--repo` by walking up for a
`.code-review-graph`, `.git` or `.svn` marker: with this directory,
`--repo platform` stops here; without it the walk reaches the repository's
`.git` and the graph widens to every sister project and all of `vendor/`.

It is tracked — README and all — because an empty directory is invisible to a
clone, and a clone without it builds the wrong graph without saying so.

    uv run pf code build          # first build, ~10s for this tree
    uv run pf code impact <file>  # callers, dependents, tests that cover it
    uv run pf code check          # is the wiring still true?

The graph database itself is build output: gitignored, gate-denied, never
committed. Rebuild it rather than carrying it.

Questions about models, columns, metrics or lineage do not belong here. Those
are `pf kg` and the `pf` MCP server, which answer them from the data graph.
