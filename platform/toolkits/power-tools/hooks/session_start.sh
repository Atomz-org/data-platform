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
mod="root"
echo "## Session context"
echo "- repo: $(basename "$root") · branch: $(git -C "$root" branch --show-current 2>/dev/null || echo '?')"

# Active entity, resolved the same way pf.mcp.server.active_project does.
if [[ "$rel" == groups/*/projects/* ]]; then
  group="$(echo "$rel" | cut -d/ -f2)"
  project="$(echo "$rel" | cut -d/ -f4)"
  mod="groups/${group}/projects/${project}"
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
# The protocol is per execution scope, not per tool; a Claude session is the
# Session scope. One line, so the always-on cost is one line.
echo "- protocol: AGENTS.md — you are its Session scope (§0); leave a note before you finish (§5)"

# Memory: what earlier sessions — Claude's or Copilot's — learned about exactly
# this scope (root and platform always; the group and project when inside one).
# One line per note and capped, so the always-on cost is bounded the way the
# cards are; the bodies are read on demand with `pf memory show`. Silent when
# there is nothing, so a repo with no notes pays nothing for this block. This
# is what makes the memory automatic rather than a rule an agent must remember:
# it is in front of the model on turn one, whichever tool wrote it.
if [ -f "$root/.memory/MEMORY.md" ]; then
  mem="$(uv run --quiet --project "$root" pf memory show --toon --limit 8 --module "$mod" 2>/dev/null || true)"
  if [ -n "$mem" ]; then
    echo "- memory (\`pf memory show\` for the bodies):"
    printf '%s\n' "$mem" | sed 's/^/    /'
  fi
fi

# Uncommitted work, capped: the point is "there is state here", not a file list.
dirty="$(git -C "$root" status --porcelain 2>/dev/null | wc -l | tr -d ' ')"
[ "${dirty:-0}" -gt 0 ] && echo "- working tree: ${dirty} uncommitted path(s) — \`git status\` before assuming a clean base"

# The commit gate, reported ONLY when it is missing. Same reasoning as the graph
# line above: a gate that is absent rather than merely quiet is worth knowing on
# turn one, not on the turn a 21-file commit lands. Silent when installed, so a
# healthy repo pays nothing for this line.
if [ -d "$root/.git" ] && [ ! -e "$root/.git/hooks/pre-commit" ]; then
  echo "- ⚠ NO COMMIT GATE (.git/hooks/pre-commit missing). gate.yaml's denylist"
  echo "  and maxFiles are enforced there and nowhere else — commits are unchecked."
  echo "  Install it: \`pf install-hook\`"
fi

exit 0
