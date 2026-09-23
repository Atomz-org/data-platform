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
  uv run pf gate --commits "${range[*]}" || status=1
done

exit "$status"
