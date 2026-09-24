# Improvements

Technical debt found while doing something else. One entry per finding: what is
wrong, how it was established, and what it would take to fix. An entry leaves
when the thing is fixed, not when it is explained.

The rule this file exists to serve: a session that notices a problem outside
its own scope records it here rather than widening its scope to fix it, or
quietly leaving it for the next person to rediscover.

---

## I-0001 — `impact_required` is dead for every dbt model

**Status:** open · **Found:** 2026-09-24 · **Severity:** high

`gate.yaml` declares that changing a dbt model requires the blast radius to be
reported first:

```yaml
impact_required:
  - "**/transform/models/**/*.sql"
  - "**/transform/macros/**/*.sql"
```

Neither entry can ever fire. `check_path` consults `autoMergeAllowlist` before
`impact_required`, and the allowlist carries a blanket `**/*.sql`, so every SQL
path in the repository resolves to `allow` first.

Verified against a real path rather than a synthetic one:

```
groups/globex/projects/globex-core/transform/models/utils/metricflow_time_spine.sql
  verdict=allow  rule=allowlist:**/*.sql
```

**Why it matters.** `platform/hooks/pre_tool_use.py` prints the blast radius
only on `result.verdict == "warn"`. Because the verdict is `allow`, that branch
is unreachable, so the PreToolUse hook never shows the blast radius for a model
edit. `LOOP.md` lists this exact failure as one it had already caught and
fixed — *"Agent skips the impact gate. Observed in this repo: staging was
regenerated, three marts broke, zero impact reports in the window."* The
precedence puts part of that fix back.

**Not yet established:** whether `pf check` or the `impact-sentinel` loop
demand impact through a path that does not go through `check_path`. If one of
them does, the exposure is limited to the hook rather than to the whole
control. That is the first thing to find out.

**Candidate fixes**, in rough order of preference:

1. Consult `impact_required` before `autoMergeAllowlist` in `check_path`. A
   warning does not block a merge, so an allowlisted path can still warn. This
   is a one-line change plus the precedence test that currently pins the
   opposite, and it is the only option that keeps both rules honest.
2. Narrow `autoMergeAllowlist` so `**/*.sql` no longer covers
   `**/transform/models/**`.
3. Decide the rule is genuinely unwanted and delete it, so the policy stops
   claiming a control it does not have.

Doing nothing is the one option that is not available, because the policy
currently reads as though the control exists.

**Pinned by:** `platform/tests/gate/test_gate_rule_reachability.py`
(`KNOWN_UNREACHABLE_IMPACT_RULES`). The freeze keeps a *new* impact rule from
silently joining these two; it does not fix these two.

---

## I-0002 — Agent network egress is unrestricted

**Status:** partly addressed · **Found:** 2026-09-24 · **Severity:** medium

Originally filed as "no devcontainer". `.devcontainer/` now exists and closes
the filesystem half: only this repository is mounted, the container runs as a
non-root user with `--cap-drop ALL` and `no-new-privileges`, and no host
credentials are mounted. That is the part that needed a boundary rather than a
rule — everything in `gate.yaml` and the hooks is policy an agent could in
principle be talked around; a mount namespace is not.

**Still open: network egress.** A process inside the container can still reach
the internet. Restricting it needs an egress proxy or a firewall on the
container network, and neither is configured. `.devcontainer/README.md` says so
plainly rather than letting the word "container" imply an isolation that is not
there — which matters most for exactly the case the container was built for,
running an agent you do not fully trust.

---

## I-0003 — Eight subsystems of the vardportal review were never read

**Status:** open · **Found:** 2026-09-24 · **Severity:** low

`docs/VARDPORTAL-GOVERNANCE-PORT.md` rests on 12 of 20 planned reader scopes.
Eight failed on a session limit and were never re-run: the staff workbench
screens, `Kits/`, the docs-site build, the Confluence and wiki publish
pipeline, `assets/inside-vardportal.html`, agent configuration and the brand
MCP server, and the disposition of the two anomalous ledger folders.

Nothing in the port plan rests on them, but the review is not complete over
that repository and should not be cited as though it is.
