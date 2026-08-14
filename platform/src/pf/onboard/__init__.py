"""Adopt an existing data repository as a project in this platform.

Onboarding splits cleanly in two, and conflating them is what makes it look
harder than it is.

**Mechanical** — scaffold the project shell, move models into this platform's
layer convention, merge dependency files, replace the orchestrator, and wire in
every capability the incoming repo does not already have. All of it is
observable from the source tree, so all of it is automated here.

**Semantic** — annotations, mart grains, declared foreign keys, ontology fit.
None of it is in the source repository, because an ordinary dbt project never had
to record it. It cannot be inferred, so it is not guessed: the plan ends with a
checklist, and `pf check` keeps failing until the work is done.

The dangerous state is the one in between — a project that is *present* and looks
onboarded while contributing nothing to the graph, the metrics or the gate.
`validate_project` reports missing annotations as a warning rather than an error,
so nothing blocks you there; the checklist exists so that gap is visible instead.
"""

from __future__ import annotations

from pf.onboard.orchestrator import Pipeline, Task, parse, render
from pf.onboard.run import Action, Plan, apply, plan, resolve_source
from pf.onboard.survey import LAYER_MAP, Survey, survey

__all__ = [
    "LAYER_MAP",
    "Action",
    "Pipeline",
    "Plan",
    "Survey",
    "Task",
    "apply",
    "parse",
    "plan",
    "render",
    "resolve_source",
    "survey",
]
