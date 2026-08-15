"""Case templates — the reasoning shape a toolkit ships, without the data.

A toolkit knows something worth asserting: `dbt-govern` knows that data which is
present, consistent and old is `stale_source` and not `model_logic`. That is a
platform fact, true in every warehouse, and it belongs with the toolkit.

What a toolkit cannot know is *which tables to say it about*. The moment a case
names `stg_payments` and the values `card`, `wallet`, `bank_transfer`, it has
stopped being a platform fact and become a claim about one company's warehouse —
inherited by every sister that scaffolds, most of which do not take payments at
all.

A template is the half that transfers. It carries the reasoning shape, the
expectations and the rationale, with `{{bindings}}` where the nouns go. `pf evals
gen` resolves those bindings against a project's own knowledge graph and writes
real cases, naming real models, into that project's `evals/cases/generated/`.

So the split is: **the platform owns the judgement, the project owns the data.**
Neither is useful alone, and neither can be written where the other lives.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pf.evals.case import AGENT_INPUTS, CaseError

# A binding is a fact the generator must find in the project graph before a
# template can be rendered. Keeping the set small and named is deliberate: a
# template that could run an arbitrary graph query would be a plugin system
# inside the thing that decides whether the platform is working.
SELECTORS = ("uncovered_mart", "mart", "staging_model", "source")

_PLACEHOLDER = re.compile(r"\{\{([a-z_]+)\.([a-z_]+)\}\}")


class TemplateError(ValueError):
    """A template that cannot be loaded, or asks for a binding we cannot resolve."""


@dataclass(frozen=True)
class Template:
    """One parameterised case, owned by the toolkit whose feature it exercises."""

    name: str
    agent: str
    requires: dict[str, str]
    input: dict[str, Any]
    expect: dict[str, Any]
    why: str = ""
    tags: tuple[str, ...] = ()
    toolkit: str = ""
    source: Path | None = None


def load_template(path: Path, toolkit: str = "") -> Template:
    try:
        raw = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise TemplateError(f"{path}: not valid JSON — {exc}") from exc

    name = raw.get("template")
    if not name or not isinstance(name, str):
        raise TemplateError(f"{path}: missing a string 'template' name")

    agent = raw.get("agent")
    if agent not in AGENT_INPUTS:
        raise TemplateError(
            f"{path}: 'agent' must be one of {', '.join(sorted(AGENT_INPUTS))}, "
            f"got {agent!r}")

    requires = raw.get("requires", {})
    if not isinstance(requires, dict):
        raise TemplateError(f"{path}: 'requires' must be an object")
    for binding, selector in requires.items():
        if selector not in SELECTORS:
            raise TemplateError(
                f"{path}: binding {binding!r} asks for unknown selector "
                f"{selector!r}. Known: {', '.join(SELECTORS)}")

    inputs = raw.get("input")
    if not isinstance(inputs, dict):
        raise TemplateError(f"{path}: 'input' must be an object")
    missing = set(AGENT_INPUTS[agent]) - set(inputs)
    if missing:
        raise TemplateError(f"{path}: agent '{agent}' needs input keys {sorted(missing)}")

    expect = raw.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise TemplateError(f"{path}: 'expect' must be a non-empty object")

    # Every placeholder must name a declared binding, or rendering would emit a
    # case with `{{mart.name}}` still in it — which loads, runs, and grades a
    # question about a table called "{{mart.name}}".
    for ref_binding, field in _PLACEHOLDER.findall(json.dumps({"i": inputs, "e": expect})):
        if ref_binding not in requires:
            raise TemplateError(
                f"{path}: uses {{{{{ref_binding}.{field}}}}} but does not require "
                f"a binding named {ref_binding!r}")

    return Template(
        name=name, agent=agent, requires=requires, input=inputs, expect=expect,
        why=raw.get("why", ""), tags=tuple(raw.get("tags", ())),
        toolkit=toolkit, source=path,
    )


def discover_templates(root: Path, toolkits: set[str] | None = None) -> list[Template]:
    """Every template every installed toolkit ships."""
    out: list[Template] = []
    for tdir in sorted((root / "platform" / "toolkits").glob("*/evals/templates")):
        toolkit = tdir.parent.parent.name
        if toolkits and toolkit not in toolkits:
            continue
        for path in sorted(tdir.rglob("*.json")):
            out.append(load_template(path, toolkit=toolkit))
    return out


# --------------------------------------------------------------- binding ----
@dataclass(frozen=True)
class Binding:
    """A resolved project fact — one real node, with the fields a template may
    interpolate."""

    name: str
    grain: str = "?"
    columns: str = ""
    column: str = ""
    layer: str = ""
    # Every identifier a generated expression is allowed to name — the real
    # column names plus the model itself. Interpolated as a list, not a string,
    # which is what makes the `references_only` hallucination check groundable.
    identifiers: tuple[str, ...] = ()

    def field(self, key: str) -> Any:
        if key not in {"name", "grain", "columns", "column", "layer", "identifiers"}:
            raise TemplateError(
                f"no field {key!r} on a binding. Available: name, grain, columns, "
                f"column, layer, identifiers")
        value = getattr(self, key)
        return list(value) if isinstance(value, tuple) else str(value)


def resolve_bindings(graph_path: Path, requires: dict[str, str]) -> dict[str, Binding] | None:
    """Find one real node per required binding, or None if the project has none.

    Returning None rather than raising is the point: a project scaffolded an hour
    ago has no marts, and "cannot ground this template yet" is a normal state, not
    an error. The generator reports it and moves on.
    """
    from pf.kg.store import open_graph

    if not graph_path.exists():
        return None

    with open_graph(graph_path, read_only=True) as g:
        marts = [m for m in g.nodes("Model") if m.layer == "marts"]
        staging = [m for m in g.nodes("Model") if m.layer == "staging"]
        sources = g.nodes("Source")

        covered: set[str] = set()
        for metric in g.nodes("Metric"):
            for e in g.in_edges(metric.id):
                covered.add(e.src)
        uncovered = [m for m in marts if m.id not in covered]

        pools = {
            "uncovered_mart": uncovered or marts,
            "mart": marts,
            "staging_model": staging,
            "source": sources,
        }

        resolved: dict[str, Binding] = {}
        for binding, selector in requires.items():
            pool = pools.get(selector) or []
            if not pool:
                return None
            node = pool[0]
            cols = [g.node(e.dst) for e in g.out_edges(node.id)]
            named = [c for c in cols if c and c.kind == "Column"]
            rendered = ", ".join(
                f"{c.name}({c.props.get('role') or c.props.get('data_type') or '?'})"
                for c in named)
            resolved[binding] = Binding(
                name=node.name,
                grain=str(node.props.get("grain", "?")),
                columns=rendered,
                column=named[0].name if named else "id",
                layer=node.layer,
                identifiers=(node.name, *(c.name for c in named)),
            )
    return resolved


def render(template: Template, bindings: dict[str, Binding]) -> dict[str, Any]:
    """Render one template into a case object, ready to be written as JSON."""

    def substitute(value: Any) -> Any:
        if isinstance(value, str):
            # A string that is *only* a placeholder takes the field's real type,
            # so a list-valued field lands as a list rather than its repr. Any
            # other string interpolates textually.
            whole = _PLACEHOLDER.fullmatch(value)
            if whole:
                return bindings[whole.group(1)].field(whole.group(2))
            return _PLACEHOLDER.sub(
                lambda m: str(bindings[m.group(1)].field(m.group(2))), value)
        if isinstance(value, list):
            return [substitute(v) for v in value]
        if isinstance(value, dict):
            return {k: substitute(v) for k, v in value.items()}
        return value

    grounded = ", ".join(sorted(b.name for b in bindings.values()))
    return {
        "name": template.name,
        "agent": template.agent,
        "why": template.why,
        "tags": list(template.tags),
        "input": substitute(template.input),
        "expect": substitute(template.expect),
        # Provenance, so a reader can tell a generated case from a hand-written
        # one without diffing against the toolkit, and knows regenerating will
        # overwrite it.
        "generated": {
            "template": template.name,
            "toolkit": template.toolkit,
            "grounded_on": grounded,
        },
    }


def validate_rendered(case: dict[str, Any], origin: str) -> None:
    """A rendered case must be a valid case.

    Checked before anything is written. Catches a template whose input keys or
    expectations do not match the agent it names — a defect in the toolkit, which
    would otherwise surface as a broken file in someone else's project.
    """
    from pf.evals.case import validate_case

    try:
        validate_case(case, origin=origin)
    except CaseError as exc:
        raise TemplateError(f"template rendered an invalid case — {exc}") from exc
