"""What leaving costs: everything a group owns, and which of it the repo can remove.

`pf bootstrap` is thirteen steps of "ensure present" and there was never an
inverse. Removing a tenant was `rm -rf groups/<g>` plus a checklist that existed
in nobody's head, and every item missed failed *silently*: an orphan workflow
that never fires again (and blocks every PR if it is a required check), a Dagster
code location pointing at a path that is gone, rows in the shared observability
database that the control-plane UI keeps charting as current spend, and an object
store that bills for a departed client's review diffs forever.

So the plan is the product. `pf offboard <group>` deletes nothing by default; it
enumerates, and it sorts what it finds into three kinds, because they need three
different things from a human:

- **regenerates** — derived from the roster, correct again as soon as the
  directory is gone and something re-runs. Nothing to do.
- **removes** — real files outside `groups/<g>/` that no generator will ever
  clean up. These are what `--apply` takes.
- **manual** — state in systems the repo can write to but not enumerate: the
  warehouse, the catalogue, the dlt pipeline state in a developer's home
  directory. The manifest's `resources:` block is the only record of these, which
  is why a group with an empty block gets a plan that says so rather than a plan
  that looks clean.

`--apply` refuses unless the group is in `offboarding`. Moving it there is a
separate, deliberate command, and it is what makes an export possible while the
data is still present.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from pf import groups

ARCHIVE_DIR = "groups/.archived"


@dataclass(frozen=True)
class Item:
    kind: str  # regenerates | removes | manual
    what: str
    detail: str = ""
    path: Path | None = None


@dataclass
class Plan:
    group: str
    lifecycle: str
    items: list[Item] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)

    def of(self, kind: str) -> list[Item]:
        return [i for i in self.items if i.kind == kind]

    @property
    def removable(self) -> list[Item]:
        return [i for i in self.of("removes") if i.path is not None]


def _size(path: Path) -> str:
    if not path.exists():
        return "absent"
    total = sum(p.stat().st_size for p in path.rglob("*") if p.is_file()) \
        if path.is_dir() else path.stat().st_size
    for unit, step in (("GB", 1e9), ("MB", 1e6), ("kB", 1e3)):
        if total >= step:
            return f"{total / step:.1f} {unit}"
    return f"{total} B"


def plan(root: Path, group: str) -> Plan:
    """Everything this family owns, and who is responsible for each part."""
    root = Path(root)
    gdir = root / "groups" / group
    try:
        manifest = groups.load(root, group)
        life = manifest.lifecycle
    except groups.GroupError as exc:
        manifest, life = None, "unmanaged"
        blockers = [str(exc)]
    else:
        blockers = []
    out = Plan(group=group, lifecycle=life, blockers=blockers)
    projects = [p.name for p in groups.projects_in(root, group)]

    # --- the directory itself
    if gdir.is_dir():
        out.items.append(Item("removes", f"groups/{group}/",
                              f"{len(projects)} project(s), {_size(gdir)}", gdir))

    # --- files outside the group that name it
    for project in projects:
        wf = root / ".github" / "workflows" / f"{project}.yml"
        if wf.is_file():
            out.items.append(Item(
                "removes", f".github/workflows/{project}.yml",
                "no bootstrap step deletes this; left behind it never fires again, "
                "and blocks every PR if it is a required check", wf))

    ledger = root / "groups" / group / "loop-ledger.json"
    if ledger.is_file():
        out.items.append(Item("regenerates", "the group's loop ledger",
                              "inside the directory, goes with it"))

    state = root / "STATE.md"
    if state.is_file() and f"### {group}/" in state.read_text():
        out.items.append(Item(
            "removes", "STATE.md section(s)",
            f"`### {group}/…` is only cleared by that project writing an empty "
            "entry list, and a departed group never writes again"))

    # --- derived from the roster: correct again once the directory is gone
    ws = root / "platform" / "workspace.yaml"
    if ws.is_file() and any(project in ws.read_text() for project in projects):
        out.items.append(Item("regenerates", "platform/workspace.yaml",
                              "rebuilt from the roster by the next `pf bootstrap`"))
    lock = root / "uv.lock"
    if lock.is_file() and f"groups/{group}/projects/" in lock.read_text():
        out.items.append(Item("regenerates", "uv.lock workspace members",
                              "`uv lock` drops them; `uv sync --frozen` fails loudly "
                              "until it is run"))

    # --- state the repo can write to but not enumerate
    obs_db = root / "data" / "_platform.duckdb"
    if obs_db.is_file():
        out.items.append(Item(
            "manual", "rows in data/_platform.duckdb",
            "agent runs, pipeline runs, monitors, impact reports and token budgets "
            "keep this group's rows, and the control-plane UI charts them as current"))

    resources = (manifest.resources if manifest else {}) or {}
    prefix = resources.get("artifact_prefix")
    out.items.append(Item(
        "manual", "artefact store objects",
        f"prefix {prefix} — `pf artifacts ls` to inventory, and the store's "
        "delete_prefix to reclaim" if prefix
        else "no artifact_prefix in group.yaml resources: nothing records what "
             "this family put in the bucket, and it bills until someone guesses"))

    services = resources.get("catalog_services") or []
    out.items.append(Item(
        "manual", "OpenMetadata services",
        ", ".join(str(s) for s in services) if services
        else "no catalog_services recorded in group.yaml"))

    warehouses = resources.get("warehouses") or []
    out.items.append(Item(
        "manual", "warehouses",
        json.dumps(warehouses) if warehouses
        else "no warehouses recorded in group.yaml: a cloud target keeps its "
             "schemas and keeps billing"))

    out.items.append(Item(
        "manual", "dlt pipeline state",
        "~/.dlt/pipelines/<project>_* lives in a developer's home directory, "
        f"outside this repo entirely: {', '.join(projects) or 'no projects'}"))

    out.items.append(Item("manual", "Dagster run history",
                          "regenerating workspace.yaml drops the code location but "
                          "not its runs, events or schedule ticks"))

    # --- what the contract said
    if manifest is not None:
        out.items.append(Item(
            "manual", "erasure deadline",
            f"{manifest.data.erasure_sla_days} day(s) from the offboarding date"
            if manifest.data.erasure_sla_days is not None
            else "none recorded in group.yaml — if this family was promised one, "
                 "nothing here knows about it"))
    return out


def tombstone(root: Path, group: str) -> Path:
    """What is left after the directory goes: enough to answer a later question
    about a departed tenant, and enough to stop the name being reused as if it
    were new."""
    root = Path(root)
    path = root / ARCHIVE_DIR / f"{group}.yaml"
    try:
        manifest = groups.load(root, group)
        body = manifest.to_yaml()
    except groups.GroupError:
        body = f"group: {group}\nlifecycle: archived\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).isoformat(timespec="seconds")
    path.write_text(
        f"# Archived {stamp}. The directory is gone; this is the record that it\n"
        f"# existed, what it promised, and what was left for a human to remove.\n"
        f"archived_at: {stamp}\n{body}")
    return path


def apply(root: Path, group: str, *, keep_directory: bool = False) -> tuple[list[str], str]:
    """Remove what the repo owns, and return what was removed plus the tombstone.

    Refuses unless the group is `offboarding`. That state is a decision someone
    made with the data still in place; without it this is one typo away from
    deleting a live tenant.
    """
    root = Path(root)
    manifest = groups.load(root, group)  # raises for an unmanaged group
    if manifest.lifecycle != "offboarding":
        raise groups.GroupError(
            f"{group} is {manifest.lifecycle}; `pf group set-state {group} offboarding` "
            "first, so there is a point at which the data is still here")

    stone = tombstone(root, group)
    removed: list[str] = []
    for item in plan(root, group).removable:
        if item.path is None:
            continue
        if item.path == root / "groups" / group and keep_directory:
            continue
        try:
            if item.path.is_dir():
                shutil.rmtree(item.path)
            else:
                item.path.unlink()
        except OSError as exc:
            removed.append(f"! {item.what}: {exc}")
            continue
        removed.append(item.what)
    return removed, str(stone.relative_to(root))
