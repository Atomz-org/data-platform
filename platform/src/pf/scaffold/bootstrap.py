"""Everything a project needs beyond its files, in one ordered, idempotent place.

Why this module exists: the post-write steps used to be inlined in
`pf new-project`. That made them unreachable for projects created earlier, so
every platform capability added afterwards had to be retrofitted by hand — the
PreToolUse hook, the dbt macro-paths and the placeholder context card were all
patched across existing projects with one-off scripts. Each of those was a silent
hole until someone noticed.

Now there is exactly one list. `pf new-project` runs it; `pf bootstrap` re-runs it
over any project, new or old. Adding a capability means adding a step here, and
both paths pick it up.

Every step must be **idempotent** — `pf bootstrap --all` is expected to be run
repeatedly — and **tolerant of an empty project**: a freshly scaffolded project
has no sources, no models and no warehouse, and bootstrapping it must still work.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

#: `created` is distinct from `ok` on purpose: a step that wrote a file the
#: repository did not have is a change a reader should see, not a no-op. It is
#: still a pass — `StepResult.ok` is "not failed" — but printing it as a tick
#: would hide the one run in which the file appeared.
Status = Literal["ok", "created", "skipped", "failed"]


@dataclass
class StepResult:
    name: str
    status: Status
    detail: str = ""

    @property
    def ok(self) -> bool:
        return self.status != "failed"


@dataclass(frozen=True)
class Step:
    name: str
    why: str
    #: May return several results. A step that fans out over a variable number of
    #: things — one entry per enabled tool — would otherwise have to flatten
    #: itself into a single line, and "3 tools ok" hides which one is broken.
    run: Callable[[Path, str, str], StepResult | list[StepResult]]


# ------------------------------------------------------------------ steps --
def _ensure_dirs(root: Path, group: str, project: str) -> StepResult:
    d = _pdir(root, group, project)
    made = []
    for rel in (
        "data",
        "kg",
        "contracts",
        "mdl",
        "governance",
        ".duckdb-skills",
        "decisions",
        ".memory/notes",
        "evals/cases",
    ):
        p = d / rel
        if not p.exists():
            p.mkdir(parents=True, exist_ok=True)
            made.append(rel)
    return StepResult("directories", "ok", f"created {len(made)}" if made else "present")


def _build_graph(root: Path, group: str, project: str) -> StepResult:
    from pf.kg.build import build_graph

    counts = build_graph(_pdir(root, group, project), group=group, project=project)
    return StepResult("knowledge graph", "ok", f"{sum(counts.values())} nodes across {len(counts)} kinds")


def _render_card(root: Path, group: str, project: str) -> StepResult:
    from pf.kg.card import PROJECT_CARD_BUDGET, estimate_tokens, render_project_card

    p = render_project_card(_pdir(root, group, project), group, project)
    n = estimate_tokens(p.read_text(encoding="utf-8"))
    status: Status = "ok" if n <= PROJECT_CARD_BUDGET else "failed"
    return StepResult("context card", status, f"~{n} tokens / {PROJECT_CARD_BUDGET}")


def _render_group_card(root: Path, group: str, project: str) -> StepResult:
    from pf.kg.card import render_group_card

    render_group_card(root / "groups" / group, group)
    return StepResult("group card", "ok", "sister roster refreshed")


def _install_git_hook(root: Path, group: str, project: str) -> StepResult:
    """Link `.git/hooks/pre-commit` to the gate, if it is not linked already.

    Git does not clone `.git/hooks`, so on every fresh checkout the gate that
    refuses a hand-edited generated artefact is simply absent, and nothing says
    so until something generated is committed by hand. It was a `just hooks`
    step someone had to remember; `pf loop audit` scored its absence at ten
    points and named the checkout, which is a strange way to find out.

    An existing hook is left alone, linked or not: replacing a file in someone's
    `.git` is not a bootstrap's business, and a project using a hook manager has
    its own reasons.
    """
    gitdir = root / ".git"
    if not gitdir.is_dir():
        return StepResult("pre-commit gate", "skipped", "not a git checkout")
    hook = gitdir / "hooks" / "pre-commit"
    if hook.exists() or hook.is_symlink():
        return StepResult("pre-commit gate", "ok", "installed")
    target = root / "platform" / "hooks" / "pre_commit.sh"
    if not target.is_file():
        return StepResult("pre-commit gate", "skipped", "no platform/hooks/pre_commit.sh")
    try:
        hook.parent.mkdir(parents=True, exist_ok=True)
        # Relative, so the link keeps working if the checkout moves.
        hook.symlink_to(Path("..") / ".." / "platform" / "hooks" / "pre_commit.sh")
    except OSError as exc:
        return StepResult("pre-commit gate", "failed", str(exc))
    return StepResult("pre-commit gate", "ok", "linked to platform/hooks/pre_commit.sh")


def _group_manifest(root: Path, group: str, project: str) -> StepResult:
    """`groups/<g>/group.yaml`: created if absent, and its template version
    raised once the steps below have backfilled what that version promises.

    A group created before the manifest existed is adopted as `provisioned`, not
    `active`. Bootstrap can see that the plumbing is in place; it cannot see that
    a human meant to take the family live, and `active` is what makes the gates
    strict. Promotion is `pf group set-state <g> active`, which is a decision.
    """
    from pf import groups

    try:
        if groups.exists(root, group):
            manifest = groups.load(root, group)
            if not manifest.behind_template:
                return StepResult("group manifest", "ok", f"v{manifest.template_version}, {manifest.lifecycle}")
            was = manifest.template_version
            manifest.template_version = groups.TEMPLATE_VERSION
            # In place, so the family's own comments survive a template bump.
            if not groups.set_key(manifest.path, "template_version", groups.TEMPLATE_VERSION):
                groups.save(manifest)
            return StepResult("group manifest", "ok", f"template v{was} -> v{groups.TEMPLATE_VERSION}")
        # The archetype already lives in the ontology instance for every group
        # scaffolded before the manifest; carry it over rather than asking again.
        domain = ""
        instance = root / "groups" / group / "ontology" / "instance.yaml"
        if instance.is_file():
            import yaml

            try:
                domain = str((yaml.safe_load(instance.read_text()) or {}).get("domain", "") or "")
            except yaml.YAMLError:
                domain = ""
        groups.save(
            groups.Manifest(
                group=group,
                path=groups.manifest_path(root, group),
                domain=domain,
                lifecycle="provisioned",
                template_version=groups.TEMPLATE_VERSION,
            )
        )
        return StepResult("group manifest", "ok", "created, lifecycle: provisioned")
    except groups.GroupError as exc:
        return StepResult("group manifest", "failed", str(exc))


def _group_plugin_and_loops(root: Path, group: str, project: str) -> StepResult:
    """Two group files the scaffold did not always write, created only if absent.

    The group marketplace lists `./.claude` as a plugin, but a plugin directory
    without `.claude-plugin/plugin.json` is skipped without a message, so every
    group scaffolded before the manifest was templated had a plugin that was
    listed, enabled in each sister's settings and never loaded. `loops.yaml`
    came later still, and a group without one cannot waive a finding or lower a
    loop's autonomy.

    Per project like the group card, because bootstrap runs per project, and
    written only when missing: both files are hand-edited after scaffolding,
    and a step that regenerated them would erase the family's decisions.
    """
    from pf.scaffold.generator import GROUP_LOOPS, GROUP_PLUGIN, write

    gdir = root / "groups" / group
    created = []
    for rel, template in (
        (Path(".claude") / ".claude-plugin" / "plugin.json", GROUP_PLUGIN),
        (Path("loops.yaml"), GROUP_LOOPS),
    ):
        if not (gdir / rel).exists():
            write(gdir / rel, template, {"group": group})
            created.append(rel.as_posix())
    return StepResult("group plugin + loops", "ok", f"created {', '.join(created)}" if created else "present")


def _export_mdl(root: Path, group: str, project: str) -> StepResult:
    """The BI/agent projection. Emitted even when empty so the path is stable and
    a consumer can be pointed at it before the first model exists."""
    from pf.projections.mdl import export as export_mdl

    path = export_mdl(_pdir(root, group, project), group, project)
    import json

    m = json.loads(path.read_text(encoding="utf-8"))
    return StepResult("MDL manifest", "ok", f"{len(m['models'])} model(s), {len(m['relationships'])} relationship(s)")


def _export_owl(root: Path, group: str, project: str) -> StepResult:
    """Platform-level and shared, so it is written once rather than per project."""
    from pf.projections.owl import export as export_owl
    from pf.projections.owl import stats

    export_owl(root / "platform" / "src" / "pf" / "ontology" / "ontology.owl")
    s = stats()
    return StepResult("OWL export", "ok", f"{s['classes']} classes, {s['object_properties']} object properties")


def _vendor_docs(root: Path, group: str, project: str) -> StepResult:
    """Regenerate the provenance docs from the registry.

    Platform-level and idempotent, so it is written once rather than per project.
    Generated for the same reason everything else here is: a hand-written page
    beside a machine-read registry is two accounts of one fact, and one of them
    goes quietly wrong.
    """
    from pf.kg.card import estimate_tokens
    from pf.vendor.card import VENDOR_CARD_BUDGET, render_card, render_doc

    render_doc(root)
    card = render_card(root)
    n = estimate_tokens(card.read_text(encoding="utf-8"))
    status: Status = "ok" if n <= VENDOR_CARD_BUDGET else "failed"
    return StepResult("vendor docs", status, f"card ~{n} / {VENDOR_CARD_BUDGET} tokens")


def _export_otop(root: Path, group: str, project: str) -> StepResult:
    """The governance projection, with this project's evidence resolved live.

    Per project rather than platform-wide because the policies are shared but the
    evidence is not: the same rule passes in one project and fails in another,
    and a manifest that averaged them would be true of nowhere.
    """
    from pf.projections.otop import build_manifest, stats
    from pf.projections.otop import export as export_otop

    d = _pdir(root, group, project)
    export_otop(root, group, project, d)
    s = stats(build_manifest(root, group, project, d))
    unknown = s.get("evidence_unknown", 0)
    return StepResult(
        "otop manifest",
        "ok",
        f"{s.get('constraint', 0)} constraint(s), "
        f"{s.get('evidence', 0)} evidence" + (f", {unknown} unproven" if unknown else ""),
    )


def _build_reporting(root: Path, group: str, project: str) -> StepResult:
    """Regenerate the Evidence layer, but only where it was opted into.

    Skipped rather than created when `reporting/` is absent: the reporting layer
    is a capability, and bootstrap must not silently enable one nobody asked for.
    """
    from pf.tools.evidence import bootstrap_project

    d = _pdir(root, group, project)
    r = bootstrap_project(root, group, project, d, {})
    return StepResult("reporting", r.status, r.detail)


def _group_notify(root: Path, group: str, project: str) -> StepResult:
    """The group's delivery channel file, for groups scaffolded before it existed.

    Group-level, so it is written once per family and not once per sister; the
    step is still per project because bootstrap is, and the second sister finds
    it present.
    """
    import re

    from pf.scaffold.generator import GROUP_NOTIFY, render

    f = root / "groups" / group / "notify.yaml"
    if f.exists():
        return StepResult("notify channel", "ok", "present")
    ctx = {"group": group, "group_upper": re.sub(r"[^A-Z0-9]+", "_", group.upper())}
    f.write_text(render(GROUP_NOTIFY, ctx), encoding="utf-8")
    return StepResult("notify channel", "ok", f"wrote {f.relative_to(root)}")


def _capability_policies(root: Path, group: str, project: str) -> StepResult:
    """Regenerate the capability policy overlay from the registry.

    Platform-scope, not project-scope: the file is one per repository and a pure
    function of `CAPABILITIES`. It runs inside the per-project loop anyway because
    that is where every other regeneration runs, and writing an identical file
    eight times is cheaper than a second place for steps to live.

    Idempotent by construction — same registry, same bytes. The step reports the
    policy count rather than a diff, because a changed count is the thing worth
    noticing in a bootstrap log.
    """
    from pf.capabilities import (
        defaults,
        policy_additions,
        resolve,
        write_capability_policies,
    )

    caps = resolve(defaults())
    before = (
        (root / "platform" / "src" / "pf" / "ontology" / "policy.capabilities.yaml").read_text()
        if (root / "platform" / "src" / "pf" / "ontology" / "policy.capabilities.yaml").exists()
        else ""
    )
    path = write_capability_policies(root, caps)
    n = len(policy_additions(caps))
    verb = "unchanged" if path.read_text() == before else "rewritten"
    return StepResult("capability policies", "ok", f"{n} policy(ies) from {len(caps)} capability(ies), {verb}")


def _claude_settings(root: Path, group: str, project: str) -> StepResult:
    """Migrate this project's `.claude/settings.json` to the current schema.

    The scaffolder wrote two keys in shapes Claude Code rejects — `enabledPlugins`
    as a list, and marketplace sources holding a bare path where the source *kind*
    belongs. Fixing the template only helps projects written after it, and this is
    the failure the module docstring above describes: a hole that stays silent
    until someone notices. A rejected settings file loads none of the plugins it
    declares, `power-tools@platform` among them, so the project loses `kg_search`
    and `impact_analysis` without ever saying so.

    Runs before `tools` and `capabilities` because both merge into this file, and
    merging into settings one schema version behind is what turns a repair into a
    crash. Idempotent: `normalize` reports no changes for a current file, and the
    file is only rewritten when there is something to change.
    """
    from pf.scaffold.claude_settings import ensure_plugins, normalize
    from pf.scaffold.generator import default_plugins

    path = _pdir(root, group, project) / ".claude" / "settings.json"
    if not path.exists():
        return StepResult("claude settings", "skipped", "no .claude/settings.json")
    try:
        settings = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        # Reported, not raised: a hand-edited file with a stray comma must not
        # stop the twelve steps after this one.
        return StepResult("claude settings", "failed", f"invalid JSON: {exc}")

    changes = normalize(settings)
    # Order matters: `ensure_plugins` writes into `enabledPlugins` as a record,
    # which is only what it is once `normalize` has migrated it.
    changes += ensure_plugins(settings, default_plugins(group))
    if not changes:
        return StepResult("claude settings", "ok", "current")
    path.write_text(json.dumps(settings, indent=2) + "\n")
    return StepResult("claude settings", "ok", "; ".join(changes))


def _bootstrap_tools(root: Path, group: str, project: str) -> list[StepResult]:
    """Every tool this project enables, set up idempotently.

    One step for all tools rather than a step per tool: which tools exist is not
    knowable here — a third party can add one by installing a package — so the
    list has to be resolved at run time. This is the seam that makes a tool reach
    projects created before it existed, exactly as this module does for platform
    steps.
    """
    from pf.tools import bootstrap_tools, enabled_names

    names = enabled_names(root, group, project)
    if not names:
        return [StepResult("tools", "skipped", "none enabled (`pf tool enable`)")]
    return bootstrap_tools(root, group, project)


def _bootstrap_capabilities(root: Path, group: str, project: str) -> list[StepResult]:
    """Every default-enabled capability, applied to this project if it is missing.

    The sibling of `_bootstrap_tools`, and it exists for the same failure: a
    capability used to reach only the projects whose author passed `--with`, so
    the impact-gate workflow existed for one project out of eight and nobody
    could see that from inside the other seven.

    Backfill applies a capability only when **every** file it writes is absent,
    never when some already exist. `pf.capabilities.apply` rewrites each target
    wholesale, and not every target is fully generated: `transform/profiles.yml`
    is seeded once and then hand-maintained — projects carry `extensions:` and
    per-target comments that `PROJECT_TARGETS` does not know about, and
    `_dbt_wiring` deliberately only *appends* absent targets rather than
    regenerating it. A partial backfill would silently delete that.

    So a partially-present capability is reported, not applied: switching it on
    rewrites a file someone edited, and that is a decision to take deliberately
    with `pf capability-add`. A fresh project has none of the files, so
    `pf new-project` still gets the whole default set.
    """
    from pf.capabilities import CAPABILITIES, defaults, gate_additions, render
    from pf.capabilities import apply as apply_capability
    from pf.cli import _merge_gate_rules

    d = _pdir(root, group, project)
    ctx = {"group": group, "project": project, "module": project.replace("-", "_")}
    out: list[StepResult] = []

    for name in defaults():
        cap = CAPABILITIES[name]
        # Merged for every default capability, not only for one being applied
        # now. The files and the gate rules are written by two different calls,
        # so an interrupt between them left a project whose generated artefacts
        # nothing denies — and the file check below would then report the
        # capability "present" forever and never reach the merge again.
        # `_merge_gate_rules` dedups, so repeating it costs nothing.
        _merge_gate_rules(gate_additions([cap]))
        # `.github/**` belongs to the repository, not the project — the same
        # split `pf.capabilities.apply` makes when writing.
        targets = [(root if rel.startswith(".github/") else d) / rel for rel in (render(r, ctx) for r in cap.files)]
        present = [t for t in targets if t.exists()]
        if len(present) == len(targets):
            out.append(StepResult(f"capability:{name}", "ok", "present"))
            continue
        if present:
            out.append(
                StepResult(
                    f"capability:{name}",
                    "skipped",
                    f"{len(present)}/{len(targets)} file(s) already exist "
                    f"(would rewrite {present[0].name}) — "
                    f"`pf capability-add {name} {group} {project}` to apply deliberately",
                )
            )
            continue
        try:
            written = apply_capability(cap, root, d, ctx)
        except Exception as exc:  # noqa: BLE001 — one capability must not stop the rest
            out.append(StepResult(f"capability:{name}", "failed", str(exc)))
            continue
        out.append(StepResult(f"capability:{name}", "ok", f"added {len(written)} file(s)"))

    if not out:
        return [StepResult("capabilities", "skipped", "none default-enabled")]
    return out


def _group_air(root: Path, group: str, project: str) -> list[StepResult]:
    """The group's `air.yaml`, if it has none.

    The sibling of `_bootstrap_capabilities`, one level up. A capability reaches
    a *project*; the family-level declaration has no capability to carry it, and
    a group scaffolded before `pf.air` existed would otherwise have no baseline
    for its sisters to inherit — so `pf air gate` would pass for the whole family
    by finding nothing to check.

    Written only when absent, never rewritten. It is hand-maintained: the whole
    point of the file is that a human decided what the family commits to, and a
    bootstrap that regenerated it would erase that decision on every run.

    The scaffolded baseline is empty, exactly as `pf new-group` writes it.
    `pf air baseline <group> --suggest` proposes what already passes; accepting
    the proposal stays a person's act.
    """
    from pf.scaffold.generator import GROUP_AIR, write

    path = root / "groups" / group / "air.yaml"
    if path.exists():
        return [StepResult("group air.yaml", "ok", f"{path.relative_to(root)} present")]
    write(path, GROUP_AIR, {"group": group})
    return [
        StepResult(
            "group air.yaml",
            "created",
            f"{path.relative_to(root)} — empty baseline; `pf air baseline {group} --suggest` proposes one",
        )
    ]


def _ci_workflow(root: Path, group: str, project: str) -> StepResult:
    """One workflow per project, composed from every job its capabilities declare.

    Replaces the file-per-capability arrangement, where each capability shipped a
    whole `.github/workflows/<thing>-<project>.yml`. Sixteen files for eight
    projects, each with its own trigger, its own path filter and its own
    checkout, and no single place that answered "what does CI do for this
    project". The per-capability files this supersedes are removed here rather
    than left behind, because leaving them means every PR runs both.

    Which jobs apply is asked, not assumed: a tool switched off in this project's
    `tools.yaml` does not contribute its job, so opting out of recce removes the
    review job rather than leaving a job that fails.
    """
    from pf.capabilities import CAPABILITIES, defaults
    from pf.scaffold.ci import legacy_paths, render_project_workflow, workflow_path
    from pf.tools import enabled_names

    try:
        names = set(defaults()) | set(enabled_names(root, group, project))
    except Exception:  # noqa: BLE001 — a broken tool registry must not stop bootstrap
        names = set(defaults())

    jobs: dict[str, str] = {}
    for name in sorted(names):
        cap = CAPABILITIES.get(name)
        if cap is not None:
            jobs.update(cap.ci_jobs)

    target = root / workflow_path(project)
    if not jobs:
        return StepResult("ci workflow", "skipped", "no capability contributes a job")

    target.parent.mkdir(parents=True, exist_ok=True)
    content = render_project_workflow(group, project, jobs)
    changed = not target.exists() or target.read_text(encoding="utf-8") != content
    if changed:
        target.write_text(content, encoding="utf-8")

    removed = []
    for rel in legacy_paths(project):
        old = root / rel
        if old.exists():
            old.unlink()
            removed.append(Path(rel).name)

    detail = f"{len(jobs)} job(s): {', '.join(sorted(jobs))}"
    if removed:
        detail += f" · superseded {', '.join(removed)}"
    elif not changed:
        detail += " · current"
    return StepResult("ci workflow", "ok", detail)


PLATFORM_WORKFLOW = """\
# GENERATED by `pf bootstrap`. Do not hand-edit — the next bootstrap regenerates
# it. Change `PLATFORM_WORKFLOW` in pf.scaffold.bootstrap instead.
#
# The platform had no CI at all. Every tenant's workflow tested that tenant, and
# the one change with fleet-wide blast radius — the shared engines, the gate, the
# scaffolder — was the only change nothing ran. `pf tokens`, `pf check` and
# `pf loop audit` were likewise written to be enforcing and wired into nothing.
name: platform

on:
  pull_request:
    paths:
      - "platform/**"
      - "pyproject.toml"
      - "uv.lock"
      - "gate.yaml"
      - "groups/*/group.yaml"
      - ".github/workflows/platform.yml"

concurrency:
  group: platform-${{ github.event.pull_request.number }}
  cancel-in-progress: true

permissions:
  contents: read

jobs:
  tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
        with:
          enable-cache: true
      - run: uv sync
      - run: uv run pytest platform/tests -q
      # `platform` only: a group's own code is linted by that group's project
      # workflow, and a platform change should not be blocked by lint debt in a
      # tenant it never touched.
      - run: uv run ruff check platform

  # The gates that were written to enforce and then never wired to anything.
  gates:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0          # pf check reports the blast radius of the diff
      - uses: astral-sh/setup-uv@v5
        with:
          enable-cache: true
      - run: uv sync
      - name: Always-on context budget
        run: uv run pf tokens
      - name: Ontology conformance and blast radius
        run: uv run pf check
      - name: Every family is onboarded
        run: uv run pf group verify
      - name: Per-family loop readiness
        run: uv run pf loop audit --per-group

  # The reconciler, as a gate. `pf bootstrap` is thirteen idempotent steps that
  # backfill whatever the scaffold gained since a project was created — and
  # nothing ran it, so four of five groups sat for months without the plugin
  # manifest and the loop overrides it writes. Drift is only invisible while
  # nobody compares.
  converged:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      # Submodules, because `docs/VENDOR-CARD.md` reports each upstream `ok` or
      # `drift` by comparing the vendored checkout against the lock. Without them
      # every upstream reads `ok` — not because nothing drifted, but because
      # there is nothing to compare — so the card regenerated here disagreed with
      # the one a developer commits, and the gate failed on a difference it had
      # manufactured itself.
      #
      # Fetched pin by pin, because `submodules: recursive` is all-or-nothing:
      # the deleted `asqav-compliance` upstream aborted this checkout and the job
      # never reached `pf bootstrap`. An unreachable pin is named in a warning
      # instead of taking the comparison down with it.
      - name: Vendored upstreams
        run: |
          failed=""
          for path in $(git config -f .gitmodules --get-regexp '^submodule\\..*\\.path$' | awk '{print $2}'); do
            git submodule update --init "$path" >/dev/null 2>&1 || failed="$failed $path"
          done
          [ -z "$failed" ] || echo "::warning title=Vendored upstreams unreachable::$failed"
      - uses: astral-sh/setup-uv@v5
        with:
          enable-cache: true
      - run: uv sync

      # Build every project's graph before anything is compared.
      #
      # The architecture maps and the generated expectations tests are rendered
      # from `transform/target/manifest.json`, which `dbt parse` writes out of
      # committed sources — annotations and dbt models, no warehouse anywhere in
      # it. Without this step the graph holds no models, every count reads zero,
      # nine maps regenerate as "none yet" and the job reports drift that is
      # really a missing build. The per-project `architecture` job already says
      # exactly this in its own comment and builds first for exactly this
      # reason; this job did not, and was red on all nine maps at once.
      #
      # Not best-effort: a build that fails here would send the comparison back
      # to measuring an empty graph, which is the bug rather than a degraded
      # version of the check.
      - name: Build the graphs the maps are generated from
        run: |
          for d in groups/*/projects/*/; do
            g=$(basename "$(dirname "$(dirname "$d")")")
            p=$(basename "$d")
            echo "::group::$g/$p"
            uv run pf kg build "$g" "$p"
            echo "::endgroup::"
          done

      - run: uv run pf bootstrap --all
      - name: The generated tree matches the committed one
        # --ignore-submodules=dirty: a vendored submodule with local build
        # output is a working-tree condition, not a generated-tree mismatch,
        # and bootstrap never writes into vendor/.
        #
        # The exclusions are projections of a *built warehouse*, not of the
        # scaffold. MDL, the catalogue, recce's plan and the whole reporting
        # layer are read from the DuckDB file, which is not in git, so a bare
        # checkout regenerates them empty — an 8-line MDL against a committed
        # 1654-line one — and the gate would fail on every PR forever while
        # reporting nothing about drift. Those are covered by `tests` and
        # `recce`, which build a warehouse before they compare.
        #
        # The architecture maps are deliberately *not* excluded, though they
        # were long assumed to belong here. They come from the dbt manifest,
        # which the build step above writes from committed sources, so a fresh
        # clone reproduces them exactly — once it builds. Excluding them would
        # have left the one artefact a platform change can silently invalidate
        # across all nine projects unchecked, since the per-project workflows
        # only fire on their own project's paths.
        #
        # `package-lock.yml` is excluded for the opposite reason to the rest: it
        # is reproducible, just not from this repository. `packages.yml` pins
        # ranges (`>=1.3.0, <2.0.0`), so `dbt deps` resolves against the package
        # registry at the moment it runs and the lock changes when dbt-labs
        # publishes, not when anyone here commits. Gating on it would fail this
        # job on somebody else's release.
        run: |
          if ! git diff --exit-code --ignore-submodules=dirty -- . \
              ':(exclude)**/kg/graph.json' \
              ':(exclude)**/mdl/mdl.json' \
              ':(exclude)**/catalog/*.json' \
              ':(exclude)**/governance/otop.json' \
              ':(exclude)**/transform/recce.yml' \
              ':(exclude)**/reporting/**' \
              ':(exclude)**/transform/models/_reporting__exposures.yml' \
              ':(exclude)**/transform/package-lock.yml'; then
            echo "::error::pf bootstrap --all changed tracked files, so the"
            echo "::error::committed tree is behind the scaffold. Run it"
            echo "::error::locally and commit what it writes."
            exit 1
          fi
"""


def _platform_workflow(root: Path, group: str, project: str) -> StepResult:
    """CI for the platform itself, which had none.

    Platform-level like the OWL export and the vendor docs: written on every
    bootstrap, identical every time, so it exists regardless of which project
    happened to be bootstrapped. It is generated rather than hand-written
    because `gate.yaml` denies `.github/workflows/**` to agents, and the reason
    holds — the gate that judges a change is not the change's to edit.
    """
    path = root / ".github" / "workflows" / "platform.yml"
    if path.is_file() and path.read_text() == PLATFORM_WORKFLOW:
        return StepResult("platform CI", "ok", "current")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(PLATFORM_WORKFLOW)
    return StepResult("platform CI", "ok", ".github/workflows/platform.yml")


def _register_code_location(root: Path, group: str, project: str) -> StepResult:
    """An unregistered project silently never runs in Dagster."""
    from pf.cli import all_projects

    lines = [
        "# GENERATED by `pf bootstrap`. Re-run after adding a project.",
        "#",
        "# One code location per project: a failure or reload in one sister never",
        "# affects another, and each gets its own process.",
        "#",
        "# Absolute on purpose: Dagster resolves a relative working_directory",
        "# against the process cwd, not against this file, so a relative path",
        "# silently resolves outside the repo. That makes the file machine",
        "# specific, which is why it is generated and not committed — tracked,",
        "# it recorded whose checkout last ran bootstrap and conflicted on every",
        "# onboarding.",
        "load_from:",
    ]
    n = 0
    for g, p, d in all_projects():
        module = p.replace("-", "_")
        if not (d / "src" / module / "definitions.py").exists():
            continue
        lines += [
            "  - python_module:",
            f"      module_name: {module}.definitions",
            f"      working_directory: {(d / 'src').resolve()}",
            f"      location_name: {g}__{p}",
        ]
        n += 1
    (root / "platform" / "workspace.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return StepResult("dagster code location", "ok", f"{n} location(s)")


def _dbt_wiring(root: Path, group: str, project: str) -> StepResult:
    """Keep an existing project's dbt config in step with the platform's.

    Two things drift, and both drift silently. A project scaffolded before a
    dialect toolkit existed has no `macro-paths` entry for it, so every `sf_*`
    call site in it fails to compile with "macro not found" — an error that
    points at the model rather than at the missing path. And a project with no
    `base` target cannot be diffed by Recce at all, because Recce compares two
    built states and there is nowhere to build the other one.

    Rewritten in place rather than regenerated, so a project's own edits to its
    dbt_project.yml survive. Text-level for `macro-paths` because a YAML
    round-trip would reflow the whole file and lose the comments explaining why
    the platform macros are on the path in the first place.

    A third thing is wired rather than drifted: a group's shared seeds. See
    `_wire_group_package`.
    """
    import yaml

    from pf.onboard.dialect import TOOLKITS
    from pf.runtime.targets import default_warehouse
    from pf.scaffold.generator import (
        PROJECT_TARGETS,
        render_target,
        replace_target,
    )

    d = _pdir(root, group, project)
    changed: list[str] = []

    dbt_yml = d / "transform" / "dbt_project.yml"
    if dbt_yml.exists():
        text = dbt_yml.read_text(encoding="utf-8")
        try:
            paths = [str(p) for p in (yaml.safe_load(text) or {}).get("macro-paths") or []]
        except yaml.YAMLError:
            paths = []
        wanted = [f"../../../../../platform/toolkits/{t}/macros" for t in TOOLKITS]
        missing = [w for w in wanted if not any(w in p for p in paths)]
        if missing and "macro-paths:" in text:
            lines = text.splitlines()
            out, inserted = [], False
            for i, line in enumerate(lines):
                out.append(line)
                nxt = lines[i + 1] if i + 1 < len(lines) else ""
                if (
                    not inserted
                    and line.lstrip().startswith("- ")
                    and any(p in line for p in paths)
                    and not nxt.lstrip().startswith("- ")
                ):
                    out += [f'  - "{m}"' for m in missing]
                    inserted = True
            if inserted:
                dbt_yml.write_text("\n".join(out) + "\n", encoding="utf-8")
                changed.append(f"macro-paths += {len(missing)}")

    note = _wire_group_package(root, group, d)
    if note:
        changed.append(note)

    profiles = d / "transform" / "profiles.yml"
    if profiles.exists():
        text = profiles.read_text(encoding="utf-8")
        try:
            doc = yaml.safe_load(text) or {}
        except yaml.YAMLError:
            doc = {}
        outputs = next((v.get("outputs") or {} for v in doc.values() if isinstance(v, dict) and "outputs" in v), {})
        # Only ever adds. A project that has retargeted `prod` at a real
        # warehouse must not have it reset to the DuckDB default by a step whose
        # job is to fill gaps.
        absent = [n for n in PROJECT_TARGETS if outputs and n not in outputs]
        if absent:
            text = text.rstrip("\n") + "\n" + "".join(render_target(n, PROJECT_TARGETS[n]) for n in absent)
            profiles.write_text(text, encoding="utf-8")
            changed.append(f"profiles += {', '.join(absent)}")

        # Point `prod` at the production warehouse, if it is still the DuckDB
        # placeholder.
        #
        # The placeholder exists so a scaffolded project builds before anyone has
        # decided where production lives. Left there it is a quiet lie: `prod`
        # names a target that is a local file, so `DBT_TARGET=prod dbt build`
        # succeeds, writes nothing anyone can see, and reports success. Seven of
        # eight projects were in that state.
        #
        # Guarded on the placeholder's *path*, not on the adapter type. The type
        # alone cannot tell the scaffold's local file from a deliberate DuckLake
        # target — both are `type: duckdb` — and guarding on type is how
        # `pf capability-add ducklake` got silently reverted to Snowflake by the
        # very next bootstrap. Only the `PF_DUCKDB_PATH` local file is the
        # placeholder; anything else — Snowflake set by hand, BigQuery from
        # `pf capability-add`, a `ducklake:` catalog — is a decision, and this
        # step must never take a project off its own warehouse. Only the `prod`
        # block is touched: `replace_target` is text-level precisely so
        # hand-added keys on the DuckDB targets beside it survive.
        wh = default_warehouse()
        if wh is not None and outputs:
            prod = outputs.get("prod") or {}
            placeholder = prod.get("type") == "duckdb" and "PF_DUCKDB_PATH" in str(prod.get("path", ""))
            if placeholder:
                # `output_for`, not `output`: the destination defaults carry a
                # `{{module}}` token so each tenant lands in its own schema, and
                # this path writes the block straight into profiles.yml with no
                # render pass of its own. Unrendered it would set the schema to
                # the literal token.
                new_text, swapped = replace_target(text, "prod", wh.output_for(project))
                if swapped:
                    profiles.write_text(new_text, encoding="utf-8")
                    changed.append(f"prod -> {wh.name}")
            elif prod:
                # Name the engine the way an operator would. DuckLake reports as
                # itself, not as the `duckdb` adapter that happens to drive it.
                engine = (
                    "ducklake" if str(prod.get("path", "")).startswith("ducklake:") else str(prod.get("type") or "?")
                )
                if engine != wh.name:
                    changed.append(f"prod already on {engine}, left alone")

    if not changed:
        return StepResult("dbt wiring", "ok", "macro-paths and targets current")
    return StepResult("dbt wiring", "ok", "; ".join(changed))


def _wire_group_package(root: Path, group: str, d: Path) -> str:
    """Install `groups/<group>/shared/transform` as a local dbt package.

    Only once the group ships a seed. Pointing a project's `seed-paths` at the
    shared directory looks equivalent and is not: dbt writes each file's compiled
    output at `target/<path relative to the project>`, so a `../../../shared`
    path lands generated SQL and seed copies beside the project, outside every
    ignore rule. A package compiles under `target/<package>/` instead.

    Macros are unaffected — sisters keep loading the shared `macros` through
    their own macro-paths, so calls stay unqualified. Appended as text so the
    file's comments survive, and re-parsed before writing so an unusual layout
    is reported rather than corrupted.
    """
    import os

    import yaml

    shared = root / "groups" / group / "shared" / "transform"
    if not (shared / "dbt_project.yml").exists() or not any((shared / "seeds").glob("*.csv")):
        return ""
    transform = d / "transform"
    packages = transform / "packages.yml"
    rel = Path(os.path.relpath(shared, transform)).as_posix()

    def wired(text: str) -> bool:
        try:
            listed = (yaml.safe_load(text) or {}).get("packages") or []
        except yaml.YAMLError:
            return False
        return any(isinstance(p, dict) and p.get("local") == rel for p in listed)

    text = packages.read_text() if packages.exists() else "packages:\n"
    if wired(text):
        return ""
    new = text.rstrip("\n") + f"\n  - local: {rel}\n"
    if not wired(new):
        return f"group seeds not wired — add `- local: {rel}` to packages.yml"
    packages.write_text(new)
    return f"packages += {group} shared (local)"


def _project_atlas(root: Path, group: str, project: str) -> StepResult:
    """The project's own atlas, and the config that decides when it refreshes.

    The config is written only when absent — it is a decision a project owns,
    and a bootstrap that reset it every run would quietly undo an opt-out. The
    page itself is regenerated every time, because it is a projection.
    """
    from pf import atlas

    d = _pdir(root, group, project)
    cfg_path = d / atlas.CONFIG_NAME
    seeded = ""
    if not cfg_path.exists():
        cfg_path.write_text(atlas.default_yaml())
        seeded = "atlas.yaml written; "

    cfg = atlas.load_config(root, group, project)
    out = atlas.write(root, group, project, cfg)
    if out is None:
        return StepResult("project atlas", "skipped", f"{seeded}disabled in atlas.yaml")
    f = atlas.gather(root, group, project)
    return StepResult(
        "project atlas", "ok", f"{seeded}{out.name} · {f.nodes} node(s) · on: {', '.join(cfg.phases) or 'request only'}"
    )


def _render_architecture(root: Path, group: str, project: str) -> StepResult:
    """The on-demand map of this project — every feature, present or not.

    Runs near the end deliberately: it reports on the CI workflow, the Dagster
    registration and the dbt targets that earlier steps create, so running it
    first would draw a project as missing three things it acquired seconds later.

    Unmapped entries are reported but do not fail the step. A directory the
    feature registry does not know about is a gap in `pf.architecture.FEATURES`,
    which is platform code — failing eight projects' bootstrap for one missing
    registry entry blames the wrong person. `pf arch --check` fails on it, in CI,
    where the platform is what is being changed.
    """
    from pf.architecture import ARCHITECTURE_BUDGET, write
    from pf.kg.card import estimate_tokens

    path, a = write(root, group, project)
    n = estimate_tokens(path.read_text())
    status: Status = "ok" if n <= ARCHITECTURE_BUDGET else "failed"
    detail = f"~{n} tokens / {ARCHITECTURE_BUDGET}, {len(a.gaps)} gap(s)"
    if a.unmapped:
        detail += f" · {len(a.unmapped)} unmapped: {', '.join(a.unmapped[:3])}"
    return StepResult("architecture map", status, detail)


def _validate(root: Path, group: str, project: str) -> StepResult:
    from pf.ontology.validate import validate_project
    from pf.runtime.dbt_runtime import validate_paths

    d = _pdir(root, group, project)
    issues = validate_project(d) + validate_paths(d)
    errors = [i for i in issues if i.severity == "error"]
    if errors:
        return StepResult("conformance", "failed", "; ".join(str(i) for i in errors[:3]))
    return StepResult("conformance", "ok", f"{len(issues)} warning(s)" if issues else "clean")


def _dev_serving(root: Path, group: str, project: str) -> StepResult:
    """`docs/quack.md` — the served dev database, and its guardrails, on paper.

    Regenerated, not written-once: the doc states enforced behaviour
    (read-only wire, localhost binding, token containment, recorded custody),
    and a stale statement about a guardrail is worse than none. Projects
    scaffolded before the serving layer existed pick the doc up here.
    """
    from pf.scaffold.generator import PROJECT_QUACK_DOC, render

    path = _pdir(root, group, project) / "docs" / "quack.md"
    ctx = {"group": group, "project": project, "module": project.replace("-", "_")}
    content = render(PROJECT_QUACK_DOC, ctx)
    if path.exists() and path.read_text() == content:
        return StepResult("dev serving", "ok", "docs/quack.md current")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return StepResult("dev serving", "ok", "docs/quack.md written")


STEPS: list[Step] = [
    Step("directories", "every generated artefact has a stable home", _ensure_dirs),
    Step(
        "knowledge graph",
        "kg_search, impact and the PreToolUse gate need a graph from day one, not after the first seed",
        _build_graph,
    ),
    Step("context card", "the always-on index every session loads", _render_card),
    Step("group card", "sister roster, so a new project is visible to its siblings", _render_group_card),
    Step(
        "pre-commit gate",
        "git does not clone .git/hooks, so on a fresh checkout the gate is absent and nothing says so",
        _install_git_hook,
    ),
    Step(
        "group manifest",
        "a group is an object with an owner, a lifecycle and a template version, not just a directory",
        _group_manifest,
    ),
    Step(
        "group plugin + loops",
        "a group scaffolded before either existed has a plugin that never loads and no loop overrides file",
        _group_plugin_and_loops,
    ),
    Step("MDL manifest", "the BI / WrenAI projection; stable path before first model", _export_mdl),
    Step("OWL export", "RDF-XML for external ontology tooling", _export_owl),
    Step(
        "otop manifest",
        "policy and evidence as an OpenTopology 0.2 graph; validated against the vendored schema",
        _export_otop,
    ),
    Step(
        "vendor docs",
        "provenance stays generated, so it cannot drift from the registry the tooling reads",
        _vendor_docs,
    ),
    Step(
        "capability policies",
        "an obligation a capability introduces must be inspectable and enforceable, not prose in a skill",
        _capability_policies,
    ),
    Step(
        "claude settings",
        "a settings file the schema rejects loads none of the plugins it declares, silently",
        _claude_settings,
    ),
    Step(
        "tools",
        "a tool enabled for the group must reach every sister, including projects created before it existed",
        _bootstrap_tools,
    ),
    Step(
        "capabilities",
        "a default-enabled capability must reach every project, including ones scaffolded before it was a default",
        _bootstrap_capabilities,
    ),
    Step(
        "reporting",
        "dashboards are a projection of the metrics, regenerated rather than hand-maintained",
        _build_reporting,
    ),
    Step(
        "platform CI",
        "the change with fleet-wide blast radius was the only "
        "one with no CI, and the enforcing commands were wired to nothing",
        _platform_workflow,
    ),
    Step("notify channel", "where loops and answers are delivered; names an env var, never a URL", _group_notify),
    Step(
        "group air.yaml",
        "a family with no control declaration has a gate that passes by finding nothing to check",
        _group_air,
    ),
    Step(
        "ci workflow",
        "one workflow per project, composed from the jobs its capabilities declare, so CI is readable in one place",
        _ci_workflow,
    ),
    Step("dagster code location", "an unregistered project never runs", _register_code_location),
    Step(
        "dbt wiring",
        "a project scaffolded before a toolkit existed cannot "
        "compile its macros, and one with no base target cannot "
        "be diffed",
        _dbt_wiring,
    ),
    Step(
        "dev serving",
        "the served dev database and its guardrails, documented in the project rather than assumed",
        _dev_serving,
    ),
    Step(
        "project atlas",
        "each project publishes a picture of its own graph, refreshed around its own dbt runs",
        _project_atlas,
    ),
    Step(
        "architecture map",
        "every feature of this project, present or absent, so an agent routes instead of reading the tree",
        _render_architecture,
    ),
    Step("conformance", "fail here rather than in BI", _validate),
]


def _pdir(root: Path, group: str, project: str) -> Path:
    return root / "groups" / group / "projects" / project


def bootstrap(root: Path, group: str, project: str) -> list[StepResult]:
    """Run every step. Failures are reported, not raised: one broken step must not
    leave a project half-registered."""
    results: list[StepResult] = []
    for step in STEPS:
        try:
            out = step.run(root, group, project)
        except Exception as exc:  # noqa: BLE001 — a step failing is data, not a crash
            results.append(StepResult(step.name, "failed", f"{type(exc).__name__}: {exc}"[:200]))
            continue
        results.extend(out if isinstance(out, list) else [out])
    return results
