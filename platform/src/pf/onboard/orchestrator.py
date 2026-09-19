"""Airflow and Prefect pipelines, read structurally and re-expressed in Dagster.

## What this translates, and what it deliberately does not

It translates **structure**: the task graph, the task names, the schedule. Those
are recoverable from the source with an AST parse, and they are exactly the part
that is tedious and error-prone to redo by hand.

It does **not** translate task bodies, and that is a decision rather than a
shortfall. An Airflow `PythonOperator` body can reach into XComs, Airflow
Variables, connection objects, macros and Jinja templating, none of which have a
one-to-one Dagster equivalent. Machine-translating that produces code that
compiles, reads plausibly, and is wrong in ways a reviewer cannot see — which is
strictly worse than an empty stub, because a stub is obviously unfinished.

So every generated asset raises `NotImplementedError` pointing at the original,
and the original is copied verbatim into `migration/orchestration/` rather than
deleted. Nothing is dropped silently. The count of ported tasks is reported, and
it starts at zero on purpose: the number that matters is how many a human has
since filled in.
"""

from __future__ import annotations

import ast
import itertools
import re
from dataclasses import dataclass, field
from pathlib import Path

QUARANTINE = "migration/orchestration"


@dataclass(frozen=True)
class Task:
    """One node of the incoming task graph."""

    name: str          # task_id where declared, else the python identifier
    var: str           # the identifier it was bound to, for edge resolution
    kind: str          # operator class, or "task" for decorated functions
    lineno: int = 0


@dataclass
class Pipeline:
    """One incoming DAG or flow."""

    name: str
    source: Path
    framework: str
    schedule: str = ""
    tasks: list[Task] = field(default_factory=list)
    edges: list[tuple[str, str]] = field(default_factory=list)
    error: str = ""

    @property
    def ported(self) -> int:
        """Tasks whose logic has been carried across. Always zero at generation —
        the point of the number is that it is a human's to raise."""
        return 0


def _identifier(text: str) -> str:
    """A python identifier from an arbitrary task id."""
    out = re.sub(r"\W+", "_", text).strip("_").lower()
    if not out or out[0].isdigit():
        out = f"task_{out}"
    return out


def _literal(node: ast.AST) -> str:
    try:
        value = ast.literal_eval(node)
    except (ValueError, SyntaxError):
        return ""
    return str(value) if value is not None else ""


def _kwarg(call: ast.Call, *names: str) -> str:
    for kw in call.keywords:
        if kw.arg in names:
            return _literal(kw.value)
    return ""


def parse(path: Path) -> list[Pipeline]:
    """Extract every pipeline declared in one file."""
    text = path.read_text(errors="ignore", encoding="utf-8")
    framework = "prefect" if re.search(r"^\s*(?:from|import)\s+prefect\b", text, re.MULTILINE) \
        else "airflow"
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        return [Pipeline(name=path.stem, source=path, framework=framework,
                         error=f"could not parse: {exc}")]

    return _parse_prefect(tree, path) if framework == "prefect" \
        else _parse_airflow(tree, path)


# ------------------------------------------------------------------ airflow --
def _parse_airflow(tree: ast.AST, path: Path) -> list[Pipeline]:
    pipeline = Pipeline(name=path.stem, source=path, framework="airflow")
    by_var: dict[str, Task] = {}

    for node in ast.walk(tree):
        # dag_id / schedule, from `DAG(...)` however it is spelled
        if isinstance(node, ast.Call) and _callee(node) == "DAG":
            pipeline.name = (_kwarg(node, "dag_id")
                             or (_literal(node.args[0]) if node.args else "")
                             or pipeline.name)
            pipeline.schedule = _kwarg(node, "schedule", "schedule_interval")

        # `t = SomeOperator(task_id="x", ...)`
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            callee = _callee(node.value)
            if callee.endswith("Operator") or callee in ("TaskGroup", "task"):
                var = node.targets[0].id if isinstance(node.targets[0], ast.Name) else ""
                if var:
                    task_id = _kwarg(node.value, "task_id") or var
                    by_var[var] = Task(_identifier(task_id), var, callee, node.lineno)

        # `@task`-decorated functions (the TaskFlow API)
        if isinstance(node, ast.FunctionDef) and _has_decorator(node, "task"):
            by_var[node.name] = Task(_identifier(node.name), node.name, "task", node.lineno)

    pipeline.tasks = sorted(by_var.values(), key=lambda t: t.lineno)
    pipeline.edges = _edges(tree, by_var)
    return [pipeline]


def _callee(call: ast.Call) -> str:
    if isinstance(call.func, ast.Name):
        return call.func.id
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    return ""


def _has_decorator(fn: ast.FunctionDef, name: str) -> bool:
    for d in fn.decorator_list:
        target = d.func if isinstance(d, ast.Call) else d
        if isinstance(target, ast.Name) and target.id == name:
            return True
        if isinstance(target, ast.Attribute) and target.attr == name:
            return True
    return False


def _chain(node: ast.AST) -> list[list[str]] | None:
    """Flatten `a >> b >> [c, d]` into ordered levels of identifiers.

    `>>` chains left-associatively, so the tree has to be flattened before edges
    can be read off it. Anything that is not a plain name or list of names yields
    None — a dependency we cannot resolve is reported, never guessed.
    """
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.RShift, ast.LShift)):
        left, right = _chain(node.left), _chain(node.right)
        if left is None or right is None:
            return None
        # `a << b` means b runs first; normalise to left-to-right order.
        return left + right if isinstance(node.op, ast.RShift) else right + left
    if isinstance(node, ast.Name):
        return [[node.id]]
    if isinstance(node, (ast.List, ast.Tuple)):
        names = [e.id for e in node.elts if isinstance(e, ast.Name)]
        return [names] if names else None
    return None


def _edges(tree: ast.AST, by_var: dict[str, Task]) -> list[tuple[str, str]]:
    edges: list[tuple[str, str]] = []

    def add(upstream: str, downstream: str) -> None:
        up, down = by_var.get(upstream), by_var.get(downstream)
        if up and down and (up.name, down.name) not in edges:
            edges.append((up.name, down.name))

    for node in ast.walk(tree):
        if isinstance(node, ast.Expr):
            levels = _chain(node.value)
            if levels:
                for a, b in itertools.pairwise(levels):
                    for u in a:
                        for d in b:
                            add(u, d)

        # `a.set_downstream(b)` / `b.set_upstream(a)`
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                and node.func.attr in ("set_downstream", "set_upstream") \
                and isinstance(node.func.value, ast.Name) and node.args:
            other = node.args[0]
            targets = ([e.id for e in other.elts if isinstance(e, ast.Name)]
                       if isinstance(other, (ast.List, ast.Tuple))
                       else ([other.id] if isinstance(other, ast.Name) else []))
            for t in targets:
                if node.func.attr == "set_downstream":
                    add(node.func.value.id, t)
                else:
                    add(t, node.func.value.id)

    return edges


# ------------------------------------------------------------------ prefect --
def _parse_prefect(tree: ast.AST, path: Path) -> list[Pipeline]:
    """Prefect flows.

    Prefect expresses dependencies through ordinary Python calls inside the flow
    body rather than through a declarative graph, so there is no reliable static
    edge set to recover. Tasks are listed; the ordering is left to the human,
    and said so in the generated file rather than inferred from call order,
    which is wrong the moment anything is conditional.
    """
    out: list[Pipeline] = []
    tasks = [Task(_identifier(n.name), n.name, "task", n.lineno)
             for n in ast.walk(tree)
             if isinstance(n, ast.FunctionDef) and _has_decorator(n, "task")]

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and _has_decorator(node, "flow"):
            schedule = ""
            for d in node.decorator_list:
                if isinstance(d, ast.Call):
                    schedule = _kwarg(d, "cron", "schedule") or schedule
            out.append(Pipeline(name=_identifier(node.name), source=path,
                                framework="prefect", schedule=schedule,
                                tasks=tasks))

    if not out and tasks:
        out.append(Pipeline(name=path.stem, source=path, framework="prefect",
                            tasks=tasks))
    return out


# ----------------------------------------------------------------- rendering --
def render(pipelines: list[Pipeline], module: str) -> str:
    """Emit one Dagster module mirroring the incoming task graphs."""
    lines = [
        '"""Dagster assets migrated from an external orchestrator.',
        "",
        "GENERATED by `pf onboard`. The **structure** here is translated — task",
        "names, dependencies and schedules. The **logic** is not: every asset",
        "raises until someone ports it.",
        "",
        "That split is deliberate. Operator bodies reach into XComs, Variables,",
        "connections and Jinja templating, none of which map one-to-one onto",
        "Dagster. Generating something plausible for them would produce code that",
        "compiles and is quietly wrong; a stub is at least honestly unfinished.",
        "",
        f"Originals are preserved verbatim under `{QUARANTINE}/`.",
        '"""',
        "",
        "from __future__ import annotations",
        "",
        "from dagster import AssetExecutionContext, ScheduleDefinition, asset, define_asset_job",
        "",
    ]

    schedules: list[tuple[str, str]] = []
    for p in pipelines:
        lines.append(f"# ---- {p.name} ({p.framework}) — {p.source.name}")
        if p.error:
            lines += [f"# NOT PARSED: {p.error}",
                      f"# Port by hand from {QUARANTINE}/{p.source.name}", ""]
            continue
        if not p.tasks:
            lines += ["# No tasks recovered; the file may build its graph dynamically.",
                      f"# Port by hand from {QUARANTINE}/{p.source.name}", ""]
            continue

        upstreams: dict[str, list[str]] = {t.name: [] for t in p.tasks}
        for up, down in p.edges:
            if down in upstreams and up not in upstreams[down]:
                upstreams[down].append(up)

        for t in p.tasks:
            deps = upstreams.get(t.name) or []
            dep_arg = f", deps={deps!r}".replace("'", '"') if deps else ""
            lines += [
                f'@asset(group_name="{_identifier(p.name)}"{dep_arg})',
                f"def {t.name}(context: AssetExecutionContext) -> None:",
                (f'    """From {p.framework} {t.kind} `{t.var}`'
                 f' ({p.source.name}:{t.lineno})."""'),
                "    raise NotImplementedError(",
                f'        "port the body of {t.var} from {QUARANTINE}/{p.source.name}")',
                "",
            ]
        if p.framework == "prefect" and p.tasks:
            lines += ["# Prefect expresses ordering through ordinary calls in the flow body,",
                      "# so no dependency edges were inferred. Add `deps=` by hand.", ""]

        job = f"{_identifier(p.name)}_job"
        selection = ", ".join(f'"{t.name}"' for t in p.tasks)
        lines += [f'{job} = define_asset_job("{job}", selection=[{selection}])', ""]
        if p.schedule:
            schedules.append((job, p.schedule))

    if schedules:
        lines += [
            "# Schedules carried across from the source. Verify each one: Airflow",
            "# presets (@daily, @hourly) and timezone handling do not always survive",
            "# translation unchanged, and a schedule that is silently wrong runs the",
            "# right work at the wrong time, which is harder to notice than a failure.",
            "",
        ]
    for job, cron in schedules:
        safe = cron.replace('"', '\\"')
        lines += [
            f"# Incoming schedule: {safe}",
            f'{job}_schedule = ScheduleDefinition(job={job}, cron_schedule="{safe}")',
            "",
        ]

    return "\n".join(lines).rstrip() + "\n"
