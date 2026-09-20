"""Tests for group loop overrides, the state spine and the loop prefix.

The properties worth pinning are the ones a config file could quietly break:
that a group cannot promote a loop, that a silenced finding carries a reason,
that a typo refuses rather than does nothing, that one project's run no longer
erases another's state, and that the rules a loop reads do not bust its cache.
"""

from __future__ import annotations

import re
import textwrap
from pathlib import Path

import pytest
from pf.agents.base import cached_prefix
from pf.loops import config as loop_config
from pf.loops.config import LoopConfigError, Waiver, waived
from pf.loops.registry import BODIES, SPECS, all_specs, watch_list
from pf.loops.runner import LoopSpec, update_state
from pydantic import BaseModel


def _write(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(body))


def _loops(tmp_path: Path, body: str, group: str = "acme") -> Path:
    _write(tmp_path / "groups" / group / "loops.yaml", body)
    return tmp_path


# ---------------------------------------------------------------- resolve --
def test_no_loops_yaml_resolves_to_the_registry(tmp_path: Path) -> None:
    # every loop a group can run: the registry's and the installed tools'
    assert loop_config.resolve(tmp_path, "acme") == all_specs()
    assert loop_config.disabled(tmp_path, "acme") == {}
    assert loop_config.waivers(tmp_path, "acme", "pii-audit") == ()


def test_resolve_applies_cadence_and_budget_in_registry_order(tmp_path: Path) -> None:
    _loops(tmp_path, """\
        version: 1
        loops:
          pii-audit: {cadence: weekly}
          freshness-triage: {token_budget: 1500}
        """)
    specs = loop_config.resolve(tmp_path, "acme")
    assert list(specs) == list(all_specs())           # yaml order is not the order
    assert specs["pii-audit"].cadence == "weekly"
    assert specs["freshness-triage"].token_budget == 1500
    assert specs["freshness-triage"].cadence == SPECS["freshness-triage"].cadence
    assert specs["vendor-drift"] is SPECS["vendor-drift"]   # untouched, not copied


def test_a_disabled_loop_is_excluded_and_its_reason_reported(tmp_path: Path) -> None:
    _loops(tmp_path, """\
        loops:
          dashboard-coverage:
            enabled: false
            reason: no reporting layer in this family yet
          vendor-drift:
            enabled: false
        """)
    specs = loop_config.resolve(tmp_path, "acme")
    assert "dashboard-coverage" not in specs and "vendor-drift" not in specs
    off = loop_config.disabled(tmp_path, "acme")
    assert off["dashboard-coverage"] == "no reporting layer in this family yet"
    assert off["vendor-drift"] == "disabled in groups/acme/loops.yaml"


def test_an_unknown_loop_name_is_refused_naming_the_known_ones(tmp_path: Path) -> None:
    """`pii-audt:` must not silently leave the audit running unwaived."""
    _loops(tmp_path, "loops: {pii-audt: {enabled: false}}\n")
    with pytest.raises(LoopConfigError, match=r"unknown loop `pii-audt`.*pii-audit"):
        loop_config.resolve(tmp_path, "acme")


def test_an_unknown_key_is_refused(tmp_path: Path) -> None:
    _loops(tmp_path, "loops: {pii-audit: {token_budgets: 5}}\n")
    with pytest.raises(LoopConfigError, match="unknown key"):
        loop_config.overrides(tmp_path, "acme")


# --------------------------------------------------------------- autonomy --
def test_raising_autonomy_is_refused(tmp_path: Path) -> None:
    _loops(tmp_path, "loops: {pii-audit: {autonomy: L2}}\n")
    with pytest.raises(LoopConfigError, match=r"cannot raise autonomy.*human decision"):
        loop_config.resolve(tmp_path, "acme")


def test_raising_to_l3_is_refused_even_from_l2(tmp_path: Path) -> None:
    _loops(tmp_path, "loops: {index-refresher: {autonomy: L3}}\n")
    with pytest.raises(LoopConfigError, match="cannot raise"):
        loop_config.resolve(tmp_path, "acme")


def test_lowering_a_writing_loop_is_refused(tmp_path: Path) -> None:
    """L1 means writes nothing. A lowered index-refresher would still rebuild
    the graph, only now inside the sweep `pf loop run-all` documents as
    read-only; the yaml has to disable it instead."""
    assert SPECS["index-refresher"].autonomy == "L2" and SPECS["index-refresher"].writes
    _loops(tmp_path, "loops: {index-refresher: {autonomy: L1}}\n")
    with pytest.raises(LoopConfigError, match=r"cannot lower autonomy.*writes nothing"):
        loop_config.resolve(tmp_path, "acme")


def test_lowering_autonomy_works_for_a_loop_that_does_not_write(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(SPECS, "probe", LoopSpec(
        name="probe", description="an L2 loop that only reports",
        autonomy="L2", cadence="daily", token_budget=0, writes=False))
    monkeypatch.setitem(BODIES, "probe", lambda *a: [])
    _loops(tmp_path, "loops: {probe: {autonomy: L1}}\n")
    assert loop_config.resolve(tmp_path, "acme")["probe"].autonomy == "L1"


def test_a_group_ceiling_caps_a_level_earned_in_the_ledger(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Lower-only has to survive promotion. A loop born L1 that earned L2 in the
    ledger, under a group that allows L1, runs at L1: the born level alone would
    not hold it, which is why lowering sets `ceiling`."""
    from pf.loops import levels
    monkeypatch.setitem(SPECS, "probe", LoopSpec(
        name="probe", description="reports only", autonomy="L1",
        cadence="daily", token_budget=0, writes=False))
    monkeypatch.setitem(BODIES, "probe", lambda *a: [])
    levels.set_level(tmp_path, SPECS["probe"], "p", "L2", actor="t", reason="earned")
    assert levels.effective(tmp_path, SPECS["probe"], "p") == "L2"
    _loops(tmp_path, "loops: {probe: {autonomy: L1}}\n")
    capped = loop_config.resolve(tmp_path, "acme")["probe"]
    assert levels.effective(tmp_path, capped, "p") == "L1"


def test_the_watch_list_is_the_registry_not_a_group(tmp_path: Path) -> None:
    """One slot for the whole platform: a group that switches index-refresher
    off must not blank the list for every other group."""
    _loops(tmp_path, "loops: {index-refresher: {enabled: false}}\n")
    assert "index-refresher" not in loop_config.resolve(tmp_path, "acme")
    assert "index-refresher" in watch_list()
    assert watch_list() == [s.name for s in SPECS.values() if s.autonomy != "L1"]


def test_a_negative_or_boolean_budget_is_refused(tmp_path: Path) -> None:
    _loops(tmp_path, "loops: {pii-audit: {token_budget: -1}}\n")
    with pytest.raises(LoopConfigError, match="token_budget"):
        loop_config.resolve(tmp_path, "acme")
    _loops(tmp_path, "loops: {pii-audit: {token_budget: true}}\n")
    with pytest.raises(LoopConfigError, match="token_budget"):
        loop_config.resolve(tmp_path, "acme")


# ---------------------------------------------------------------- waivers --
def test_a_waiver_without_a_reason_is_refused(tmp_path: Path) -> None:
    _loops(tmp_path, """\
        loops:
          pii-audit:
            waivers:
              - node: dim_customers.email
        """)
    with pytest.raises(LoopConfigError, match="no reason"):
        loop_config.waivers(tmp_path, "acme", "pii-audit")


def test_waivers_are_per_loop_and_leave_the_spec_alone(tmp_path: Path) -> None:
    _loops(tmp_path, """\
        loops:
          metric-gap-harvester:
            waivers:
              - node: "rpt_*"
                reason: report tables are presentation, nothing to measure
        """)
    ws = loop_config.waivers(tmp_path, "acme", "metric-gap-harvester")
    assert ws == (Waiver("rpt_*", "report tables are presentation, nothing to measure"),)
    assert loop_config.waivers(tmp_path, "acme", "pii-audit") == ()
    assert loop_config.overrides(tmp_path, "acme")["metric-gap-harvester"].touches_spec is False


def test_waived_matches_names_and_globs_case_sensitively() -> None:
    ws = (Waiver("rpt_*", "r"), Waiver("dim_customers.email", "r"))
    assert waived("rpt_daily_sales", ws) is ws[0]
    assert waived("dim_customers.email", ws) is ws[1]
    assert waived("RPT_daily_sales", ws) is None
    assert waived("fct_orders", ws) is None


# ------------------------------------------------------------------ state --
def _body(path: Path) -> str:
    """STATE.md without its timestamp, which is the only line allowed to move."""
    return re.sub(r"^Last run: .*$", "Last run: <ts>", path.read_text(), flags=re.M)


def test_a_scoped_write_keeps_other_sections_and_legacy_lines(tmp_path: Path) -> None:
    update_state(tmp_path, ["jaffle/jaffle-shop: onboarding at stage `review`"])
    update_state(tmp_path, ["[pii-audit] PII column `dim_customers.email` reaches a mart"],
                 group="acme", project="acme-eu")
    p = update_state(tmp_path, ["[freshness-triage] futures_prices stale"],
                     watch=["index-refresher"], group="commodity", project="commodity-india")
    text = p.read_text()
    assert "- jaffle/jaffle-shop: onboarding at stage `review`" in text
    assert text.index("### acme/acme-eu") < text.index("### commodity/commodity-india")
    assert "- [pii-audit] PII column `dim_customers.email` reaches a mart" in text
    assert "- [freshness-triage] futures_prices stale" in text
    assert "- index-refresher" in text.split("## Watch list")[1]
    assert text.rstrip().endswith("path policy in `gate.yaml`.")


def test_a_scoped_write_replaces_only_its_own_section(tmp_path: Path) -> None:
    update_state(tmp_path, ["old finding"], group="acme", project="acme-eu")
    update_state(tmp_path, ["theirs"], group="acme", project="acme-us")
    update_state(tmp_path, ["new finding"], group="acme", project="acme-eu")
    text = (tmp_path / "STATE.md").read_text()
    assert "old finding" not in text
    assert "- new finding" in text and "- theirs" in text
    # Replaced in place, not appended: the section keeps its position.
    assert text.index("### acme/acme-eu") < text.index("### acme/acme-us")


def test_an_emptied_section_is_dropped(tmp_path: Path) -> None:
    update_state(tmp_path, ["finding"], group="acme", project="acme-eu")
    update_state(tmp_path, ["theirs"], group="acme", project="acme-us")
    update_state(tmp_path, [], group="acme", project="acme-eu")
    text = (tmp_path / "STATE.md").read_text()
    assert "acme-eu" not in text and "- theirs" in text
    update_state(tmp_path, [], group="acme", project="acme-us")
    assert "- (nothing outstanding)" in (tmp_path / "STATE.md").read_text()


def test_a_multi_line_finding_survives_another_projects_write(tmp_path: Path) -> None:
    """A dbt Database Error is a header plus indented lines. Written intact,
    the read-back kept only `- ` lines: the tail vanished and a continuation
    that happened to start with `- ` became a finding of its own."""
    finding = ("[test-failure-triage] model.p.fct_x: fail — Database Error in model fct_x\n"
               "  Binder Error: column \"amount\" not found\n- retried 3 times")
    update_state(tmp_path, [finding], group="acme", project="acme-eu")
    update_state(tmp_path, ["theirs"], group="commodity", project="commodity-india")
    text = (tmp_path / "STATE.md").read_text()
    assert ("- [test-failure-triage] model.p.fct_x: fail — Database Error in model fct_x "
            "Binder Error: column \"amount\" not found - retried 3 times") in text
    assert "\n- retried 3 times" not in text


def test_two_writers_on_one_project_keep_their_own_sections(tmp_path: Path) -> None:
    """`pf align status --state` and a clean `pf loop run-all` used to share
    one section: the second erased the ladder position the first had written."""
    update_state(tmp_path, ["onboarding at stage `ontology` (1/6 open)"],
                 group="acme", project="acme-eu", writer="onboarding")
    update_state(tmp_path, ["[pii-audit] leak"], watch=["index-refresher"],
                 group="acme", project="acme-eu", writer="loops")
    text = (tmp_path / "STATE.md").read_text()
    assert "### acme/acme-eu · onboarding" in text and "### acme/acme-eu · loops" in text
    update_state(tmp_path, [], watch=["index-refresher"],
                 group="acme", project="acme-eu", writer="loops")
    text = (tmp_path / "STATE.md").read_text()
    assert "- onboarding at stage `ontology` (1/6 open)" in text
    assert "· loops" not in text


def test_a_second_identical_run_is_idempotent(tmp_path: Path) -> None:
    update_state(tmp_path, ["legacy line"])
    update_state(tmp_path, ["a", "b"], watch=["index-refresher"],
                 group="acme", project="acme-eu")
    first = _body(tmp_path / "STATE.md")
    update_state(tmp_path, ["a", "b"], watch=["index-refresher"],
                 group="acme", project="acme-eu")
    assert _body(tmp_path / "STATE.md") == first


def test_an_unscoped_write_rewrites_the_whole_block(tmp_path: Path) -> None:
    update_state(tmp_path, ["theirs"], group="acme", project="acme-us")
    update_state(tmp_path, ["only this"])
    text = (tmp_path / "STATE.md").read_text()
    assert "###" not in text and "- only this" in text


def test_a_half_scoped_write_is_refused(tmp_path: Path) -> None:
    """Silently falling back to a full rewrite is the erasure this exists to end."""
    with pytest.raises(ValueError, match="both group and project"):
        update_state(tmp_path, ["x"], group="acme")


# ----------------------------------------------------------------- prefix --
def _rules_repo(tmp_path: Path) -> Path:
    _write(tmp_path / "groups" / "acme" / "CLAUDE.md", """\
        # acme — group context

        @kg/group_card.md

        - A price is a `unit_price`, never a `money_amount`.
        """)
    _write(tmp_path / "groups" / "acme" / "projects" / "acme-eu" / "CLAUDE.md", """\
        # acme-eu — project context

        @kg/context_card.md

        - Futures do not settle at weekends: a Monday breach is the calendar.
        """)
    _write(tmp_path / "groups" / "acme" / "projects" / "acme-eu" / "kg" / "context_card.md",
           "# acme-eu (generated 2026-01-01)\n\n- 3 marts\n")
    return tmp_path


def test_prefix_carries_group_and_project_rules_without_includes(tmp_path: Path) -> None:
    text = cached_prefix(_rules_repo(tmp_path), "acme", "acme-eu")[0]["text"]
    assert "<group_rules>" in text and "never a `money_amount`" in text
    assert "<project_rules>" in text and "Futures do not settle" in text
    assert "@kg/" not in text
    # The card stays last, after the rules.
    assert text.index("<project_rules>") < text.index("<context_card>")
    assert text.rstrip().endswith("</context_card>")


def test_prefix_is_byte_stable_and_survives_a_card_regeneration(tmp_path: Path) -> None:
    root = _rules_repo(tmp_path)
    first = cached_prefix(root, "acme", "acme-eu")[0]["text"]
    assert cached_prefix(root, "acme", "acme-eu")[0]["text"] == first
    card = root / "groups" / "acme" / "projects" / "acme-eu" / "kg" / "context_card.md"
    card.write_text(card.read_text().replace("2026-01-01", "2099-12-31"))
    assert cached_prefix(root, "acme", "acme-eu")[0]["text"] == first


def test_missing_rules_files_are_skipped(tmp_path: Path) -> None:
    text = cached_prefix(tmp_path, "acme", "acme-eu")[0]["text"]
    assert "<group_rules>" not in text and "<project_rules>" not in text


# ------------------------------------------------------------ rejected key --
class _Verdict(BaseModel):
    ok: bool


def test_a_rejected_key_reads_as_no_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    """A key that is set but refused takes the deterministic path the loop
    bodies already have for "no key", and says why in the run's message. As an
    SDK error it discarded the findings and tripped the breaker on a loop whose
    subject was fine."""
    import anthropic
    import httpx
    from pf.agents import base

    class _Messages:
        def parse(self, **_: object) -> None:
            req = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
            raise anthropic.AuthenticationError(
                "invalid x-api-key", response=httpx.Response(401, request=req), body=None)

    class _Client:
        messages = _Messages()

    monkeypatch.setattr(base, "client", lambda: _Client())
    with pytest.raises(base.NoCredentials, match="rejected"):
        base.call(base.AGENTS["freshness_triage"], system=[{"type": "text", "text": "x"}],
                  user="y", output_format=_Verdict, group="g", project="p")
