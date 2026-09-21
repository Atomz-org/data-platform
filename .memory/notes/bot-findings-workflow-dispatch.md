---
name: bot-findings-workflow-dispatch
description: 'How to backfill review findings into issues with the repo''s bot-findings workflow — dispatch one PR at a time, closed PRs included, epic #312 is full'
type: project
status: active
---

`.github/workflows/bot-findings.yml` + `.github/scripts/bot_findings.py` turn every CodeRabbit/Gitar (and flagged human) review comment into a `bot-finding` issue, idempotent by a `(path, title)` fingerprint stored as an HTML comment in the issue body; the comment URL is cited in the body, so "is this thread tracked?" = search issue bodies for the thread URL. It never closes issues (adds `fix-landed` instead).

Backfill: `gh workflow run bot-findings.yml -f pr=<N>` works for closed and merged PRs too (`pr=all` sweeps every PR, empty = open PRs). All `workflow_dispatch`/`schedule` runs share the `sweep` concurrency group with `cancel-in-progress: false`, so dispatching several at once leaves one queued and **cancels the rest** — dispatch sequentially and `gh run watch` each (a dispatch run takes ~30 s; PR-event runs took ~15 min because `wait_for_checks` waited for `track`'s own pending check and always hit the 900 s timeout — fixed in PR #430 by filtering the row whose URL carries this run's `GITHUB_RUN_ID`). `PROJECTS_TOKEN` is not set, so the board step is skipped. Epic #312 (Findings — Runtime & Platform) has hit GitHub's 100 sub-issue cap; new findings fail to attach with "Parent cannot have more than…". #324/#327 are a known same-fingerprint duplicate.

2026-09-19: the closed duplicate PRs #203, #213, #218, #221, #226 had never been swept; backfilling them filed #381–#396+. After that, every unresolved review thread on PRs ≥ #195 has an issue.

Closed 2026-09-20 (PR #429, merged): the workflow
read review *threads* only and skipped review *bodies*, so CodeRabbit's "Outside
diff range", "Nitpick" and (older format) severity-named sections were never
filed — 363 of them across 137 PRs, against 9 filed by hand as #400–#408.
`parse_review_body()` now walks the body's `<summary>` lines; body findings are
labelled `outside-diff`/`nitpick` and a nitpick is filed at P3.

Three things that are load-bearing and easy to break again:
- **Section resets are an explicit list** (`CR_RESET`), not "any unrecognised
  heading ends the section" — CodeRabbit phrases `♻️ Proposed change to …`
  summaries freely, and treating one as a boundary silently credited four
  files' findings to a fifth.
- **The older format glues the first finding's span onto the file summary**
  (`acme-eu.yml-76-80 (1)`); it is stripped once per file run, not per finding.
- **Legacy issues were unreachable by the index** — no `bot-finding:` marker,
  `[#N]` title prefix, and a `File:` line carrying a span. `canonical_title`
  strips the prefix, `issue_path` strips the span, `locate` treats two *equal*
  paths as one defect instead of declining, and `upsert` adopts a marker-less
  issue by writing one in. Without all four, turning body parsing on duplicates
  52 tracked issues.

Verify any change here with a dry run over every PR before merging — it is the
only thing that distinguishes "parses more" from "files duplicates":
`BOT_FINDINGS_DRY_RUN=1 GITHUB_REPOSITORY=Atomz-org/data-platform PR=<n> python3
bot_findings.py`. Last run: 363 parsed, 12 matched, 0 duplicates, 351 historic
findings still unfiled — they land only on an explicit `pr=all` dispatch, since
the nightly sweep reads open PRs only (1 open today).

**Why:** the user asked that review comments never be lost when PRs are merged; the workflow is the repo's mechanism, and reinventing it (manual `gh issue create`) would create fingerprint-less duplicates on the next nightly sweep.
**How to apply:** to "raise review comments as issues", dispatch this workflow per PR instead of filing by hand; verify with a URL match of thread → issue body. Split #312 into a new epic before more findings land. See [[pr-merge-classifier-limits]].
