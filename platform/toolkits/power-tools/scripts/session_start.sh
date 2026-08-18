#!/usr/bin/env bash
# SessionStart hook — the four facts a session needs before its first turn.
#
# stdout is injected into the model's initial context, so this is charged to
# every session for its whole life. It is deliberately short and says only what
# cannot be derived from the files already loaded: which entity is active,
# whether the gate can actually fire, and where the tree stands right now.
#
# The important line is the graph one. A project with no kg/graph.duckdb gets
# warnings instead of blast radii — the gate is present and inert. That is worth
# knowing on turn one, not on the turn an edit lands.
set -uo pipefail

cd "${CLAUDE_PROJECT_DIR:-$PWD}" 2>/dev/null || exit 0

root="$PWD"
while [ "$root" != "/" ] && ! { [ -d "$root/platform" ] && [ -d "$root/groups" ]; }; do
  root="$(dirname "$root")"
done
[ "$root" = "/" ] && exit 0

rel="${PWD#"$root"/}"
echo "## Session context"
echo "- repo: $(basename "$root") · branch: $(git -C "$root" branch --show-current 2>/dev/null || echo '?')"

# Active entity, resolved the same way pf.mcp.server.active_project does.
if [[ "$rel" == groups/*/projects/* ]]; then
  group="$(echo "$rel" | cut -d/ -f2)"
  project="$(echo "$rel" | cut -d/ -f4)"
  echo "- scope: project ${group}/${project} — never read another group or sister"

  graph="$root/$rel/kg/graph.duckdb"
  if [ ! -f "$graph" ]; then
    echo "- ⚠ NO KNOWLEDGE GRAPH (kg/graph.duckdb missing). The impact gate is inert:"
    echo "  edits are allowed but nothing verifies what they break."
    echo "  Build it before changing a model: \`pf kg build ${group} ${project}\`"
  else
    newest="$(find "$root/$rel/transform/models" -name '*.sql' -newer "$graph" 2>/dev/null | head -1)"
    if [ -n "$newest" ]; then
      echo "- ⚠ graph is STALE (models changed since it was built). A blast radius"
      echo "  computed now may be wrong. Refresh: \`pf kg build ${group} ${project}\`"
    else
      echo "- graph: current · ask it before reading files (kg_search, kg_neighbors, impact_analysis)"
    fi
  fi
else
  echo "- scope: platform/root — shared infra. Changes here affect every project."
fi

# Uncommitted work, capped: the point is "there is state here", not a file list.
dirty="$(git -C "$root" status --porcelain 2>/dev/null | wc -l | tr -d ' ')"
[ "${dirty:-0}" -gt 0 ] && echo "- working tree: ${dirty} uncommitted path(s) — \`git status\` before assuming a clean base"

exit 0
