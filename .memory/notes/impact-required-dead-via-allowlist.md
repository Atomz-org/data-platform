---
name: impact-required-dead-via-allowlist
description: Both impact_required rules in gate.yaml are outranked by autoMergeAllowlist **/*.sql, so no blast radius is demanded for any dbt model
type: project
status: active
agent: claude-code
---

check_path consults autoMergeAllowlist before impact_required. The allowlist
carries a blanket `**/*.sql`, so every dbt model resolves to `allow` first and
both impact_required entries are unreachable. Verified on a real path:
groups/globex/projects/globex-core/transform/models/utils/metricflow_time_spine.sql
returns verdict=allow rule=allowlist:**/*.sql.

**Why:** platform/hooks/pre_tool_use.py prints the blast radius only when
result.verdict == "warn". Because the verdict is `allow`, that branch is
unreachable — so the PreToolUse hook never shows a blast radius before a model
edit. LOOP.md catalogues this exact failure as one already caught and fixed
("staging was regenerated, three marts broke, zero impact reports in the
window"); the precedence puts part of it back. The existing test
test_the_allowlist_outranks_impact_required pins the behaviour but reads as a
curiosity rather than a live hole.

**How to apply:** do not assume impact is enforced because gate.yaml declares
it. Before relying on it, check whether `pf check` or the impact-sentinel loop
demand impact through a path that bypasses check_path — that is still
unestablished and decides how wide the exposure is. Logged as I-0001 in
IMPROVEMENTS.md with three candidate fixes; the precedence flip is the only one
that keeps both rules honest, since a warn does not block a merge. Pinned by
KNOWN_UNREACHABLE_IMPACT_RULES in platform/tests/gate/test_gate_rule_reachability.py,
which stops a new impact rule silently joining them but does not fix these two.
