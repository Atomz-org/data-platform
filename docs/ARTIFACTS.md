# The artefact store

Build output that git should not carry, in an S3-compatible bucket. Today that
means Recce's baselines and recorded reviews; the mechanism is not Recce-shaped
and a second producer adds its own keys without touching the store.

Code: [`platform/src/pf/artifacts.py`](../platform/src/pf/artifacts.py) (the
bucket) and the `# remote` section of
[`platform/src/pf/tools/recce.py`](../platform/src/pf/tools/recce.py) (which key
means what). CLI: `uv run pf artifacts --help`.

---

## Why

`transform/recce_state.json` and `transform/target-base/` were committed on
purpose, and `gate.yaml` still carries the reasoning: a reviewer on another
machine cannot reproduce the numbers in a summary without the baseline they were
measured against, and a CI runner has code and no warehouse, so a checkout
without them is a checkout whose review cannot run at all.

That held for seven projects at ~1.4 MB each. It did not survive jaffle-shop,
whose 996 marts make the same three files **30 MB** — larger than this
repository's entire history — rewritten whole, with fresh timestamps, on every
review run. The gate anticipated it:

> If that becomes the dominant noise in reviews, the fix is to drop these four
> lines and untrack them, not to hand-edit them.

Ignoring them alone would have been the other half of the bad trade: the CI job
and the control plane both *read* those files, so untracking without somewhere
to put them turns every review into "not exercised". A bucket is the missing
half — the producer pushes, every consumer pulls, and a 20 MB file never passes
through a diff.

## Layout

Keys mirror the repository, so the bucket reads like a checkout:

```
groups/<group>/projects/<project>/transform/
    target-base/<base-ref>/manifest.json
    target-base/<base-ref>/catalog.json
    reviews/<head-ref>/recce_state.json
    reviews/<head-ref>/recce_summary.md
```

The trailing ref segment is what git gave us for free and object storage does
not.

- **A baseline is keyed by the ref it was built from** — the branch a diff is
  *against*, `main` unless `GITHUB_BASE_REF` or `PF_ARTIFACTS_BASE_REF` says
  otherwise. It is shared: one known-good build of the trunk, published once and
  pulled by everyone diffing against it. Keying it per developer would give
  every branch a baseline captured from its own code, and a diff against
  yourself reports clean — the exact false negative `capture_baseline` builds
  into the `base` target to avoid.
- **A review is keyed by the branch under review** — `GITHUB_HEAD_REF` in CI,
  the current branch locally. Two branches reviewing the same project write two
  keys rather than racing for one, which was the conflict that made the
  committed artefacts painful.

`reviews/` has no local counterpart: on disk a review is two files in
`transform/`, because a checkout only holds one. The bucket holds every
branch's.

## Setup

The endpoint and bucket ship as defaults and need no configuration. An R2
endpoint carries the account id, which every client needs and none can act on
alone, so it is not a credential — override both with `PF_ARTIFACTS_ENDPOINT`
and `PF_ARTIFACTS_BUCKET` for a fork or a second environment.

Credentials are never in a file. Create an **R2 API token** scoped to *Object
Read & Write* on this bucket, then:

```bash
export PF_ARTIFACTS_ACCESS_KEY_ID=...
export PF_ARTIFACTS_SECRET_ACCESS_KEY=...
uv run pf artifacts status          # configured, and reachable?
```

`R2_*` and `AWS_*` are read as fallbacks so a shell that already holds S3
credentials for this bucket does not need a second copy under a third name. A
machine that talks to **both** AWS and R2 must set the `PF_` pair — otherwise
the `AWS_` fallback points this at the wrong endpoint's credentials and every
call 403s.

For CI, add the same two as **repository secrets** under exactly those names.
The generated per-project workflow passes them to the `recce` job, and
`uv sync --extra recce --extra artifacts` installs boto3 for it.

## Use

```bash
uv run pf artifacts status                        # config + reachability
uv run pf artifacts ls <group> <project>          # what has been published
uv run pf artifacts push <group> <project>        # upload; no args → every project
uv run pf artifacts pull <group> <project>        # download; no args → every project
uv run pf artifacts migrate --apply               # committed → bucket, once
```

Most of the time none of these are needed. The recce commands already do it:

| Command | Store |
|---|---|
| `pf tool recce baseline` | captures, then **publishes** under the base ref |
| `pf tool recce run` | **pulls** the baseline if none is on disk, **publishes** the review |
| `pf tool recce ci` | same, and reports *not exercised* if neither has one |
| `pf tool recce serve` | pulls both, so a fresh clone has something to render |
| `pf ui` → Review | fetches the recorded review once if it is absent |
| Dagster `recce_review` | pulls the baseline, publishes the review to the run |

**With no store configured, all of that is a silent no-op** and everything
behaves as it did when the files were local-only. That is deliberate: a
developer diffing against a baseline they built ten seconds ago has no use for a
bucket, and requiring one would tax the local-first path this platform is built
around. In CI it is not a no-op that anyone wants — a runner has no warehouse to
build a baseline from — so an unconfigured store there shows up as *review not
exercised*, which is the honest reading and not a green tick.

### Two rules worth knowing

**A local baseline wins.** `pf tool recce run` pulls only when nothing is on
disk. Re-pulling would silently replace a capture you made deliberately with
main's, changing what your next diff is measured against. Use
`pf artifacts pull --baseline` to overwrite on purpose.

**Publishing never changes a verdict.** Every upload is wrapped: a failed push
warns and the command keeps its exit code. A captured baseline that did not
upload is still a captured baseline, and a network blip should not read as a
failed build.

## Known gap: baseline staleness

A baseline is only a baseline while it matches the branch it claims to be from.
Pulled by every PR and refreshed by nobody, it drifts one commit further from
`main` on each merge — and the diffs stay green because the comparison state no
longer exists, not because nothing moved.

Refresh is manual: run `pf tool recce baseline <group> <project>` on the trunk,
which now publishes instead of asking for a commit.

This is **not** a regression from the store. Committed baselines went stale in
exactly the same way and on the same cadence; moving them to a bucket neither
fixes it nor worsens it. The fix is a `push`-triggered CI job, which the
generated workflow cannot host today — it is `pull_request`-only, and its
`changes` job diffs against `github.base_ref`, which a push does not have. That
is a change to `pf.scaffold.ci`, and it is not disguised as a change to Recce.

## Migration

`pf artifacts migrate` moves the already-committed artefacts out of git. It
pushes, **verifies every key landed with a round trip to the bucket**, and only
then runs `git rm --cached`. The order is the whole safety of the command:
untracking first would, on a failed upload, leave the artefacts nowhere — still
in git history and recoverable, but "recoverable from history" is not a state to
leave a merge gate in.

Dry by default:

```bash
uv run pf artifacts migrate            # show what would move
uv run pf artifacts migrate --apply    # push, verify, untrack
```

Then, by hand, because both files are hand-maintained and say so:

1. `.gitignore` — extend the recce block from jaffle-shop to every project.
2. `gate.yaml` — drop the `denylist_except` entries for
   `**/transform/recce_state.json`, `recce_summary.md` and `target-base/**`.
   The **denylist** entries stay: hand-editing a recorded diff still makes the
   review lie, wherever the file lives.
3. Commit the removals. `pf check` flags anything still tracked.
