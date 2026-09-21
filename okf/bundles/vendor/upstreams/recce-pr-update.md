---
type: Vendor Upstream
title: Recce PR-Update
description: Composite action keeping a PR branch merged with its base
resource: https://github.com/DataRecce/PR-Update
tags:
- vendor
- spec
- MIT
status: stable
sources:
- id: recce-pr-update:action.yml
  resource: https://github.com/DataRecce/PR-Update
  title: action.yml
---

# Recce PR-Update

A dbt diff is only meaningful when the PR branch actually contains its base. A stale branch produces a diff against code that was already replaced, which reads as a regression that does not exist. This action is the precondition for trusting anything Recce reports in CI.

## Adopted

- **action.yml** (data) -> platform/src/pf/tools/recce.py
  The generated workflow pins this action and passes `baseBranch` / `prBranch` / `autoMerge`. Renamed inputs break the workflow at run time, in CI, which is the worst place to find out — hence `data`.

## Declined

- **autoMerge defaulting to true**
  Upstream defaults to merging the base into the PR branch automatically. We generate it with autoMerge false: a merge is a write to someone's branch, and the platform's rule is that an agent reports and a human merges. The reminder comment is enough to unblock the diff.
