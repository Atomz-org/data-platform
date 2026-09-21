---
name: open-pr-stacks-2026-09
description: 'All of #196–#342 in Atomz-org/data-platform are merged (2026-09-20); what land-195.sh learned landing them, and what is still owed'
type: project
status: resolved
---

State 2026-09-19 (late): #195 and #379 are merged (user ran land-195.sh v1); main = 3c87d31. Open PRs in #196–#342, as the REST `stack` field reports them (`gh api repos/.../pulls/N --jq .stack` → number, position, size, base.ref; stack numbers share the issue sequence, so `gh stack merge <pr>` cannot collide with a stack number):

- **Stack 202** (native): #196–#201 at positions 3–8/8 (#194, #195 were 1–2). Base is the trunk `feat(proverance)--included-asqv-module`, not main — merges land in the trunk, which must be carried to main by a new PR (#379 was the last carry). Base changes on native-stack PRs are refused.
- **Quality series** #222–#252 and #329: *ordinary* PRs chained by base branch (#222 base air/08-docs = #201's head). Each must be retargeted to main once its base is on main.
- **Stack 343** (native, base main): #331–#342. `gh pr merge` on members is refused by GitHub — only `gh stack merge`.
- Singles on main: #255, #263 (needs stranded #269–#271 folded in: they merged into stack/14 after stack/14 was merged down into stack/09), #280, #318 (stranded #320, content-identical), #323, #330 (draft).
- Vendor/.gitmodules touched by #196, #198, #222, #329, #330, #339, #341.

Progress (2026-09-19 evening): #196–#201 merged (user ran resume), trunk carried to main as #409. #222's branch turned out to carry *older copies* of the seven air commits (different SHAs, same patches — `git cherry origin/main quality/01` marks them `-`), so a plain fold conflicts in 7 files and a pure-addition union duplicates the `air` capability (compiles, wrong). Correct fold = main + only the PR's own commits; land-195.sh now does this as scenario S11, and its .py union refuses duplicate top-level names / dict keys. #222's fold was prepared that way (tree 46fa3a2d, 456 tests pass) and left for the user's `resume`. After #222 lands, the old quality/01 tip is an ancestor of main, so the rest of the quality chain folds normally.

Progress (2026-09-19 night): quality chain #222–#252 and #255 merged. #263's fold was staged for `resume`. It showed that a *clean* git merge can still be wrong: main and stack/09 each added a `"ducklake"` warehouse, and git merged both into one dict where the later one silently wins. Keeping one side of a generated `.claude/settings.json` also drops the other side's tool permissions. The script now covers both: S12 checks for duplicate names and dict keys on every fold before it is committed, and settings files are merged key by key. It also records hand resolutions with rerere and rebuilds `docs/ARCHITECTURE.md` and `platform/tests/README.md` after every fold. Hand fixes beyond the conflicted files go in `<git-dir>/LAND_NOTES`, which `resume` puts into the fold commit.

#263 then made every test live in `platform/tests/<group>/`, and nearly every later PR (#318, #323, #329, #332–#336, #341) adds top-level tests. Guessing a file's group from its imports was right for only 13 of 33 existing files. So S13 uses a hand-decided `TEST_GROUPS` map in the script, and a file not in the map stops for a human. The test-index token budget was raised to 1600 in #280's fold, with the user's approval; #410 tracks replacing that with a rollup.

#318's branch had added `encoding="utf-8"` to every read_text/write_text, and main rewrote some of those same lines. The helper's `settle` resolves such conflicts hunk by hunk: when one side only added `encoding=` arguments, it takes the other side's rewrite and re-inserts them, keeping each inside the same call. If only some hunks qualify, it resolves those and leaves the rest marked. #318 also moved the `evidence` capability into `pf.tools.evidence`, so main's changes to that capability have to be carried into the tool. `resume N` stops after PR N. The user's explicit "merge #318" request let the classifier allow `resume 318`.

#318 merged on 2026-09-19 as 1b0be99, while CI was red. The script accepted GitHub's `unstable` state. The red CI exposed two real bugs on main:
- `pf arch` was registered as a command (#255) and as a group (#263), and the group won, so every project's `architecture` job failed.
- Generated files kept from branch sides on folds were stale.

PR #411 (`fix/arch-cli-collision`) routes `pf arch` to both commands and rebuilds all eight graphs and maps without local data, which is how CI builds them.

The script now has S14: before any merge it waits for CI, stops on failures main doesn't share, and treats jobs that died at checkout as non-blocking. `--allow-red` overrides.

Separate infra problem: the upstream of the `vendor/asqav-compliance` submodule (`jagmarques/asqav-compliance`) no longer exists. Every job that checks out submodules fails at checkout, including the platform `suite`, air-baseline, ASQAV and "AI control baseline". Fixing it means changing a vendor pin, which is the user's decision.

S15, added on 2026-09-19:
- `run` with no range lands every open PR, oldest to newest, into the default branch, which is detected automatically (`--base` overrides). It re-scans after each pass, so PRs opened mid-run get picked up.
- A PR that needs a human is set aside in `stopped/N.state` with its worktree kept, and `resume N` picks it back up. Later members of its stack wait; everything else carries on. `--stop-first` restores the old stop-on-first behaviour.
- `--first N` lands chosen PRs ahead of the queue. There is also a `status` command, a lock so only one run goes at a time, retries on network errors for read-only GitHub calls, and a `history` file of merges.
- Gotcha that crashed two runs: bash 5.3 reads a non-ASCII byte right after `$var` as part of the name (`#$from–`). Brace every such variable; `test_queue.sh` greps for the pattern.

Progress (2026-09-20): #263, #280, #318, #323, #411, #329–#339 merged; only #340–#342 (the tail of stack 343) remain. Four more scenarios came out of those folds:

- **S16** — before a push, rebuild what CI checks: `pf kg build` then `pf arch` for every project the PR touches, the repository-wide maps, and revert the `package-lock.yml` hashes `dbt deps` rewrites as a side effect.
- **S17** — fold the target even when git reports no conflict. #333 merged cleanly and landed an ungrouped test on main, because S12/S13/S16/--verify only ran inside folds.
- **S18** — run `ruff check platform` (what `platform.yml`'s `tests` job runs) before the push, apply only the fixes ruff calls safe, stop on the rest. #340 cost three CI rounds for nine lint errors, one of them the script's own: S13's `rehome()` rewrites a file's only `Path(__file__)` and orphans `from pathlib import Path`. S13's post-move fix-up is now `--select I,F401`.
- `cmd_resume` can rebuild a fold whose `MERGE_HEAD` was destroyed (a `git stash -u` inside a merging worktree), via `write-tree`/`commit-tree`/`update-ref HEAD` — `git update-ref MERGE_HEAD` refuses pseudorefs.

Issues filed while landing: #410 (test-index budget should be a per-group rollup, not a raised number), #412 (`kg/graph.json` records an absolute checkout path), #413 (quack server tests cannot start a server on a GitHub runner; skipped via `_ensure_or_skip`).

The scratchpad harness for the script is 10 files (`test_helper.py`, `test_format_only.py`, `test_resolve.sh`, `test_s12.sh`, `test_s13.sh`, `test_settle.sh`, `test_queue.sh`, `test_fold.sh`, `test_untracked.sh`, `test_lostmerge.sh`, `test_s18.sh`) — a test that sources a function by name needs the new name added to its `for fn in ...` list.

**Done 2026-09-20 11:53Z: every PR in #196–#342 is merged and no PR is open.** main = 055d187. Verified on a clean checkout of main: `pf check`, `pf arch check`, `pf test check`, `pf tokens`, `pf group verify`, `ruff check platform` and `pf kg check --strict` for all nine projects all pass, and the suite is 1012→1024 passed, 8 skipped. No `pf bootstrap --all` was needed — S16/S17 kept the tree consistent as each PR landed. (`pf bootstrap --all` cannot be run inside a git worktree at all: its commit-gate step does `mkdir .git/hooks`, and in a worktree `.git` is a file.)

Two more scenarios came from the last three:

- **S18** — see above, from #340.
- **dupcheck now reads package.json too**: #341's clean JSON merge left autoprefixer, git-remote-origin-url and postcss in `dependencies` *and* `devDependencies`, postcss at two different ranges. A name in two blocks where neither side had it in two is reported.
- **S16 now checks what it rebuilt**: `pf kg build` parses the dbt project and *carries on when the parse fails*, so it rebuilds a graph recording no models at all. #341 shipped eight such graphs. S16 runs `pf kg check <g> <p> --strict` after each rebuild and stops on a graph that is still not current.
- **`cmd_resume` fails fast on unstaged edits**: the check used to run after the fold was committed, so a half-finished resolution was committed before the message arrived.

The bug behind all of that: `pf report build`'s new `_exposures` wrote a header and an empty `exposures:` key for any project whose pages read nothing — eight of nine. dbt refuses the file ("the value of 'exposures' is not a list") and that one parse error takes down every command that reads the manifest. Fixed in #341: no file rather than an empty one.

Also learned the hard way: **never run `pf report build` to "resolve" a generated file.** Without `transform/target/`, `collect_metrics` finds nothing and it rewrites real pages as empty ones. Resolve a generated artefact by taking the side whose generator won, then confirm by calling the generator function directly and diffing.

Issue #414 filed: `kg/graph.json` edge order is not stable across rebuilds.

Still owed to the user: the `vendor/asqav-compliance` upstream (`github.com/jagmarques/asqav-compliance`) is gone, so every CI job that checks out submodules dies at checkout — including main's `suite`, air-baseline, ASQAV and "AI control baseline". Bumping or dropping that pin is a human decision.

`land-195.sh` at the repo root (untracked, v2) implements all of it: `plan` (read-only simulation via merge-tree/commit-tree), `issues`, `run FROM TO`, `one N`, `resume`; scenarios S1–S18 documented in its header. Its Python helper and conflict resolver are unit-tested (24 + 1 fixture test in the session scratchpad); the classifier allows Claude to run `./land-195.sh run/resume/one` because the user asked for the merges, but not a hand-written merge into main. Generated artifacts (kg, otop, mdl, project settings/workflows, VENDOR docs, workspace.yaml, uv.lock) keep the branch side on folds; `pf bootstrap --all` regenerates them afterwards.

**How to apply:** re-check PR state first; point the user at `./land-195.sh plan` then `run --allow-vendor`. Don't hand-merge what the script covers. See [[pr-merge-classifier-limits]], [[bot-findings-workflow-dispatch]].
