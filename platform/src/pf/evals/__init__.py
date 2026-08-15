"""Evals — the tests for the parts of this platform that are prompts.

Every other layer here has a way to be wrong that a type checker or a test can
catch. The agent layer does not: `triage_failures` returns a well-typed
`Diagnosis` whether or not the classification inside it is correct, and a prompt
edit that quietly turns "the test is wrong" into "the model is wrong" fails
nothing. That is the gap this package closes.

Two tiers, because "is this agent right" is two different questions:

  * **contract** — deterministic, no API key, no spend. Checks the plumbing
    around the model: that every routed step names a model we have a spec for,
    that a rendered request never carries a parameter its target rejects, that
    the cached prefix is byte-stable across runs. These are the failures that
    are invisible until a loop 400s at 3am, and they cost nothing to check, so
    they run everywhere — pre-commit, CI, `pf check`.

  * **live** — calls the real models and grades the typed fields that come back.
    This is the only tier that can tell you a prompt got worse. It costs money
    and is not perfectly repeatable, so it is opt-in (`--live`).

Cases come from three tiers, and each tier owns what only it can know:

    platform/toolkits/<toolkit>/evals/    platform features and health
    groups/<group>/evals/                 what the sisters share
    groups/<group>/projects/<p>/evals/    one entity's business logic

**Platform evals live with the feature they evaluate**, not in a corpus of their
own. A toolkit already ships the skills that describe how its feature is used;
its evals are the proof that the feature still behaves that way, and keeping the
two in one directory is what stops a skill and its evidence drifting apart.
`dbt-govern` documents the four root-cause classes, so `dbt-govern` owns the
cases that hold triage to them.

This tier is entity-agnostic by construction, which is what makes it safe to run
everywhere. It cannot encode what any company sells: business logic does not
transfer between sisters, and a case assuming one group's revenue rule would be
a bug the moment another group ran it. What transfers is the *shape of a
judgement* — data that is present, consistent and old is `stale_source` and not
`model_logic`; a 13% swing on a 40-row table is five rows and not a signal.
Those hold for any warehouse.

The group and project tiers are where entity knowledge belongs. Discovery walks
strictly downward — the named group, the named project, nothing else — so no
suite ever reads a sister.
"""

from __future__ import annotations

from pf.evals.case import Case, CaseError, discover, load_case, validate_case
from pf.evals.contract import CONTRACT_CHECKS, run_contract
from pf.evals.generate import Generated, generate
from pf.evals.grade import GradeFailure, grade
from pf.evals.runner import CaseResult, Report, run_live
from pf.evals.template import Template, TemplateError, discover_templates

__all__ = [
    "CONTRACT_CHECKS",
    "Case",
    "CaseError",
    "CaseResult",
    "Generated",
    "GradeFailure",
    "Report",
    "Template",
    "TemplateError",
    "discover",
    "discover_templates",
    "generate",
    "grade",
    "load_case",
    "run_contract",
    "run_live",
    "validate_case",
]
