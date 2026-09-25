#!/usr/bin/env bash
# Pre-push gate. Re-applies the per-commit file cap to everything being pushed.
#
# `pre-commit` is the only thing that ever applied `maxFiles`, and two ordinary
# actions walk straight past it leaving no trace that they did: `git commit
# --no-verify`, and committing in a clone where nobody has run `pf` — git never
# clones `.git/hooks`, so a fresh checkout has no gate until something installs
# one. Both produce a commit the gate never saw, and neither records the fact.
#
# So this is the second look, at the last moment the change is still local:
# every commit about to leave the machine is measured again, against the same
# `maxFiles` in the same gate.yaml, before there is a pull request to argue
# about. A commit that passed the cap at commit time passes again for free.
#
# It is not the last look either — `git push --no-verify` skips this too, which
# is why `agent-context.yml` re-applies the same rule over a pull request's
# commits on every PR. Three layers, one rule, and the rule read from one file
# in all three.
#
# Git feeds this hook one line per ref on stdin:
#   <local ref> <local sha> <remote ref> <remote sha>
set -euo pipefail
ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

status=0
while read -r _ local_sha _ remote_sha; do
  [ -n "${local_sha:-}" ] || continue
  # An all-zero local sha is a branch *deletion*: no commits to judge.
  [[ "$local_sha" =~ ^0+$ ]] && continue
  if [[ "${remote_sha:-}" =~ ^0+$ ]]; then
    # A new branch. Only what no other remote branch already carries —
    # otherwise the first push of a branch re-judges the whole of history,
    # including commits that predate this gate and cannot now be split.
    range=("$local_sha" "--not" "--remotes")
  else
    range=("$remote_sha..$local_sha")
  fi

  # `|| rc=$?` rather than `if`: the exit code is the point, and an `if` around
  # the call discards it.
  rc=0
  uv run pf gate --commits "${range[*]}" || rc=$?
  if [ "$rc" -eq 0 ]; then
    continue
  fi

  # Exit 2 is typer's usage error, and the only way to get one here is a `pf`
  # that has no `--commits`: this repository keeps one hooks directory for
  # every worktree, so a checkout whose branch predates the flag can end up
  # running a hook installed by one that has it. Blocking the push over that
  # would make an old branch unpushable for a reason its author cannot act on,
  # so it reports and stands aside. The cap is still applied on the pull
  # request by `agent-context.yml`, which is the layer that cannot be skipped.
  if [ "$rc" -eq 2 ]; then
    echo "pre-push: this checkout's pf has no 'gate --commits' — the per-commit" >&2
    echo "pre-push: file cap was NOT measured here. CI re-applies it on the PR." >&2
    continue
  fi
  status=1
done

# Generated context, named before the push. CI regenerates it and no longer
# fails on it (see agent-context.yml), so this is information, not a gate:
# committing the regenerated files keeps the diff under review whole and saves
# the bot a commit on the branch. Never blocking — it renders this working
# tree, where an untracked file the runner will never see can differ.
if [ "$status" -eq 0 ] && [ -z "${PF_SKIP_CONTEXT_CHECK:-}" ]; then
  out="$(mktemp)"
  if ! uv run pf context refresh --dry-run >"$out" 2>&1; then
    echo "pre-push: generated files this branch would change (CI regenerates them; not a failure):" >&2
    grep -E '^\s+~ ' "$out" | head -20 >&2 || true
    echo "pre-push: to include them in this push: uv run pf context refresh && commit." >&2
  fi
  rm -f "$out"
fi

exit "$status"
