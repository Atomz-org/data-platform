"""Project the policy layer as an OpenTopology (otop-core 0.2) manifest.

`policy.yaml` has always *claimed* otop's shape — intent -> constraint ->
artifact -> evidence. Claiming it and emitting it are different things: a claim
is prose, a manifest is something an external tool can read and a schema can
reject. Now that `vendor/opentopology` is pinned, the export is validated against
`schemas/otop-core-v0.2.schema.json` itself, so the claim is testable.

The canonical topology from `specs/otop-core-0.2.md` §6.6 puts Constraint at the
centre, and this follows it exactly:

    Constraint --derived_from--> Intent
    Constraint --governed_by--> Policy
    Constraint --implemented_by--> Artifact
    Constraint --verified_by--> Evidence

WHY THE EVIDENCE IS COMPUTED, NOT DECLARED. It would be easy — and worthless —
to emit `result: pass` for every rule because policy.yaml names an evidence kind.
The evidence objects here are resolved against what is actually on disk and in
the tracking DB at export time: `pf check` is run, the ledger is read, durable
artefacts are stat-ed. A rule whose evidence has never been produced exports as
`unknown`, which is the finding. An unenforced policy that reports `pass` is
worse than no policy at all, because it ends the conversation.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pf.ontology.model import Policy, load_ontology

OTOP_VERSION = 0.2
NS = "pf"
SCHEMA_REL = "vendor/opentopology/schemas/otop-core-v0.2.schema.json"

# otop timestamps are RFC 3339 normalised to UTC with a literal Z.
TS_FMT = "%Y-%m-%dT%H:%M:%SZ"


def _now() -> str:
    return datetime.now(UTC).strftime(TS_FMT)


def _git(root: Path, *args: str) -> str:
    r = subprocess.run(["git", *args], cwd=str(root), capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""


def _commit(root: Path) -> str:
    return _git(root, "rev-parse", "HEAD")


def _authored(root: Path, rel: str) -> str:
    """When a file last changed, so regenerating the manifest is not a diff.

    Object `created_at` tracks the policy, not the export. Using `now()` here
    would make every export churn and drown a real policy change in noise.

    `%cI` and convert, not `--date=format-local`. `format-local` renders the
    commit in *the exporting machine's* timezone, and TS_FMT then appends a
    literal `Z` — so the value claimed UTC while holding local time, and the
    same commit exported to two different stamps depending on where the export
    ran:

        host, TZ=+02:00     2026-08-13T22:01:06Z     <- wrong, and churned
        container, TZ=UTC   2026-08-13T20:01:06Z     <- the real instant
        git's own answer    2026-08-13T22:01:06+02:00

    Which defeated the whole point of not using `now()`: the manifest still
    churned, 42 entries at a time, whenever it was regenerated somewhere else.
    `%cI` is the committer date with its true offset, and `_as_ts` normalises
    it — the same conversion the ledger timestamps already go through.
    """
    out = _git(root, "log", "-1", "--format=%cI", "--", rel)
    return _as_ts(out) or _now()


def _digest(root: Path, rel: str) -> str:
    oid = _git(root, "rev-parse", f"HEAD:{rel}")
    return f"git:{oid}" if oid else ""


# ------------------------------------------------------------- artifacts ----
@dataclass(frozen=True)
class ArtifactRef:
    """One `enforced_by` entry, resolved to something on disk.

    policy.yaml writes enforcement three ways, and all three appear in the wild:
        pf.ontology.validate:money-without-currency   module path + rule name
        platform/hooks/pre_commit.sh                  a repo path
        gate.yaml:denylist                            a config file + key
    """

    raw: str
    id: str
    title: str
    artifact_type: str
    path: str
    symbol: str
    language: str


def _artifact(root: Path, raw: str) -> ArtifactRef:
    ref, _, symbol = raw.partition(":")
    if "/" in ref or ref.endswith((".py", ".sh", ".yaml", ".yml", ".sql")):
        path = ref
    else:
        path = "platform/src/" + ref.replace(".", "/") + ".py"

    suffix = Path(path).suffix
    language = {".py": "python", ".sh": "bash", ".sql": "sql"}.get(suffix, "yaml")
    if suffix in (".yaml", ".yml"):
        kind = "configuration"
    elif "hooks/" in path:
        kind = "hook"
    elif ".loops." in ref or "/loops/" in path:
        kind = "loop"
    else:
        kind = "check"

    slug = raw.replace("/", ".").replace(":", ".").replace("_", "-")
    return ArtifactRef(raw=raw, id=f"artifact.{NS}.{slug}", title=raw,
                       artifact_type=kind, path=path, symbol=symbol,
                       language=language)


# -------------------------------------------------------------- evidence ----
@dataclass(frozen=True)
class Observation:
    result: str          # pass | fail | unknown | waived | not_applicable
    observed_at: str
    detail: str = ""


def _observe(root: Path, project_dir: Path | None, kind: str,
             group: str = "", project: str = "") -> Observation:
    """Resolve one evidence kind against reality.

    Deliberately conservative: anything we cannot check right now is `unknown`,
    never `pass`. `not_applicable` is reserved for evidence that is genuinely
    out of scope (a project-scoped artefact when exporting platform-wide), so it
    stays distinguishable from "we did not look".
    """
    now = _now()

    if kind == "pf check":
        if project_dir is None:
            return Observation("not_applicable", now, "platform-scope export")
        try:
            from pf.ontology.validate import validate_project

            issues = validate_project(project_dir)
            errs = [i for i in issues if i.severity == "error"]
            return Observation("fail" if errs else "pass", now,
                               f"{len(errs)} error(s), {len(issues)} issue(s)")
        except Exception as exc:  # noqa: BLE001 — an unrunnable check is `unknown`
            return Observation("unknown", now, f"{type(exc).__name__}: {exc}"[:120])

    if kind == "pf gate":
        gate = root / "gate.yaml"
        return (Observation("pass", now, "denylist present") if gate.exists()
                else Observation("unknown", now, "no gate.yaml"))

    if kind.startswith("pf loop run "):
        loop = kind.removeprefix("pf loop run ").strip()
        return _from_ledger(root, loop, now, group, project)

    if kind.startswith("pf tool recce"):
        # Resolved from the artefacts on disk rather than by re-running anything.
        # `unknown` is the honest answer for a project that has never been
        # reviewed — see the module note: anything we cannot check right now is
        # never `pass`.
        if project_dir is None:
            return Observation("not_applicable", now, "platform-scope export")
        from pf.tools.recce import config_file, has_baseline, state_file

        if kind == "pf tool recce config":
            p = config_file(project_dir)
            if not p.exists():
                return Observation("unknown", now, "recce.yml not generated yet")
            ts = datetime.fromtimestamp(p.stat().st_mtime, UTC).strftime(TS_FMT)
            return Observation("pass", ts, str(p.relative_to(root)))

        p = state_file(project_dir)
        if not p.exists():
            return Observation(
                "unknown", now,
                "no diff recorded" if has_baseline(project_dir) else "no baseline captured")
        ts = datetime.fromtimestamp(p.stat().st_mtime, UTC).strftime(TS_FMT)
        return Observation("pass", ts, str(p.relative_to(root)))

    if kind == "impact_reports":
        try:
            from pf import obs

            n = obs.query("SELECT count(*) n FROM impact_reports")[0]["n"]
            return (Observation("pass", now, f"{n} recorded")
                    if n else Observation("unknown", now, "none recorded"))
        except Exception:
            return Observation("unknown", now, "tracking DB unavailable")

    # Durable file-backed evidence: existence is the observation.
    rel = {"STATE.md": "STATE.md", "loop-ledger.json": "loop-ledger.json"}.get(kind, kind)
    for base in ([project_dir] if project_dir else []) + [root]:
        p = base / rel
        if p.exists():
            ts = datetime.fromtimestamp(p.stat().st_mtime, UTC).strftime(TS_FMT)
            return Observation("pass", ts, str(p.relative_to(root)))
    return Observation("unknown", now, f"{rel} not produced yet")


# pf.loops.runner.Outcome, mapped to otop's evidence results. `ok` and `noop`
# both mean the loop ran to completion — `noop` is "ran, found nothing", which is
# a pass for a policy check. Everything that means "we did not get an answer"
# maps to `unknown` rather than `fail`: an unrun check is not a failed one, and
# reporting it as failed devalues the results that are real.
LEDGER_RESULT: dict[str, str] = {
    "ok": "pass",
    "noop": "pass",
    "error": "fail",
    "escalated": "fail",
    "gate_blocked": "unknown",
    "circuit_open": "unknown",
}


def _from_ledger(root: Path, loop: str, now: str,
                 group: str = "", project: str = "") -> Observation:
    p = root / "loop-ledger.json"
    if not p.exists():
        return Observation("unknown", now, "no ledger")
    try:
        doc = json.loads(p.read_text())
    except json.JSONDecodeError:
        return Observation("unknown", now, "ledger unreadable")
    runs = doc.get("runs") if isinstance(doc, dict) else doc
    # Scoped to this project. The ledger is repo-wide, and an unfiltered lookup
    # let one company's clean pii-audit stand as evidence that another company's
    # PII policy holds — which is precisely the cross-entity assumption this
    # platform is built to prevent.
    hits = [r for r in (runs or [])
            if isinstance(r, dict) and r.get("loop") == loop
            and (not project or r.get("project") == project)
            and (not group or r.get("group") == group)]
    if not hits:
        where = f" for {group}/{project}" if project else ""
        return Observation("unknown", now, f"{loop} has never run{where}")
    last = hits[-1]
    # The ledger's field is `outcome`; reading `status` returned None for every
    # run, which fell through to "not ok" and exported a clean pii-audit as a
    # policy failure.
    outcome = str(last.get("outcome") or last.get("status") or "").lower()
    when = str(last.get("started_at") or last.get("ts") or "")
    return Observation(LEDGER_RESULT.get(outcome, "unknown"),
                       _as_ts(when) or now,
                       f"{loop}: {outcome or 'no outcome recorded'}"
                       + (f" ({len(last.get('findings') or [])} finding(s))"
                          if last.get("findings") else ""))


def _as_ts(value: str) -> str:
    """Ledger timestamps are ISO with an offset; otop wants UTC ending in Z."""
    if not value:
        return ""
    try:
        return datetime.fromisoformat(value).astimezone(UTC).strftime(TS_FMT)
    except ValueError:
        return ""


# ---------------------------------------------------------------- export ----
def _obj(oid: str, kind: str, title: str, created: str, **extra: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "id": oid, "kind": kind, "title": title, "lifecycle": "active",
        "metadata": {"created_at": created, "actor": "pf.projections.otop"},
    }
    base.update(extra)
    return base


def _rel(src: str, verb: str, dst: str, created: str, **meta: Any) -> dict[str, Any]:
    return {
        "id": f"rel.{src}.{verb.replace('_', '-')}.{dst}",
        "from": src, "to": dst, "type": verb,
        "metadata": {"created_at": created, **meta},
    }


def build_manifest(root: str | Path, group: str = "", project: str = "",
                   project_dir: str | Path | None = None) -> dict[str, Any]:
    """Emit the policy layer as an otop-core 0.2 manifest.

    Scope is a choice, not an accident. Policies and their enforcing artifacts
    are platform-wide, so they are identical in every project; evidence is not,
    because `pf check` passes in one project and fails in another. Passing a
    project produces the same governance skeleton with that project's observed
    results attached.
    """
    root = Path(root)
    pdir = Path(project_dir) if project_dir else None
    onto = load_ontology()
    commit = _commit(root)
    policy_created = _authored(root, "platform/src/pf/ontology/policy.yaml")

    scope = f"{group}/{project}" if project else "platform"
    graph_id = f"otop.{NS}.{scope.replace('/', '.')}"

    objects: list[dict[str, Any]] = []
    relationships: list[dict[str, Any]] = []

    policy_id = f"policy.{NS}.data-platform"
    objects.append(_obj(
        policy_id, "policy", "Agentic Data Platform governance policy",
        policy_created,
        extensions={"scope": scope, "source": "platform/src/pf/ontology/policy.yaml",
                    "rules": len(onto.policies)}))

    seen_artifacts: dict[str, dict[str, Any]] = {}

    for p in onto.policies:
        intent_id = f"intent.{NS}.{p.id}"
        constraint_id = f"constraint.{NS}.{p.id}"

        objects.append(_obj(intent_id, "intent", _headline(p), policy_created,
                            extensions={"statement": p.intent}))
        objects.append(_obj(
            constraint_id, "constraint", f"{p.id}", policy_created,
            modality="MUST" if p.severity == "error" else "SHOULD",
            constraint_type=p.constraint,
            checkability="automated" if p.enforced else "manual",
            assertion=_assertion(p),
            expression_language="pf.ontology.policy/1",
            severity=p.severity,
            extensions={"applies_to": p.applies_to, "params": p.params}))

        relationships.append(_rel(constraint_id, "derived_from", intent_id,
                                  policy_created, confidence="high",
                                  method="human_review"))
        relationships.append(_rel(constraint_id, "governed_by", policy_id, policy_created))

        for raw in p.enforced_by:
            a = _artifact(root, raw)
            if a.id not in seen_artifacts:
                locator: dict[str, Any] = {"repository": _origin(root), "commit": commit,
                                           "path": a.path, "language": a.language}
                if a.symbol:
                    locator["symbol"] = a.symbol
                d = _digest(root, a.path)
                if d:
                    locator["digest"] = d
                seen_artifacts[a.id] = _obj(
                    a.id, "artifact", a.title, _authored(root, a.path),
                    artifact_type=a.artifact_type, language=a.language, locator=locator,
                    extensions={"exists": (root / a.path).exists()})
            relationships.append(_rel(constraint_id, "implemented_by", a.id,
                                      policy_created,
                                      implemented_at=policy_created))

        for kind in p.evidence:
            o = _observe(root, pdir, kind, group, project)
            ev_id = f"evidence.{NS}.{p.id}.{_slug(kind)}"
            objects.append(_obj(
                ev_id, "evidence", f"{kind} for {p.id}", o.observed_at,
                evidence_type=_evidence_type(onto, kind),
                result=o.result,
                subjects=[{"id": constraint_id, "kind": "constraint",
                           "relationship_type": "verified_by"}],
                provenance={"actor": "pf.projections.otop", "scope": scope,
                            "detail": o.detail},
                metadata={"created_at": o.observed_at, "observed_at": o.observed_at,
                          "actor": "pf.projections.otop"}))
            relationships.append(_rel(constraint_id, "verified_by", ev_id,
                                      o.observed_at, verified_at=o.observed_at))

    objects.extend(seen_artifacts.values())

    return {
        "otop_version": OTOP_VERSION,
        "graph": {
            "id": graph_id,
            "title": f"Policy and evidence — {scope}",
            "repository": _origin(root),
            "commit": commit,
            "metadata": {"created_at": _now(), "actor": "pf.projections.otop"},
        },
        "objects": objects,
        "relationships": relationships,
        "extensions": {
            "pf": {"scope": scope, "group": group, "project": project,
                   "unenforced": [p.id for p in onto.unenforced_policies()]},
        },
    }


def _headline(p: Policy) -> str:
    text = " ".join(p.intent.split())
    return text if len(text) <= 160 else text[:157] + "..."


def _assertion(p: Policy) -> str:
    """A one-line, readable restatement of the constraint plus its parameters."""
    parts = [p.constraint]
    if p.params:
        parts.append("(" + ", ".join(f"{k}={v}" for k, v in p.params.items()) + ")")
    if p.applies_to:
        parts.append("on " + ", ".join(f"{k}={v}" for k, v in p.applies_to.items()))
    return " ".join(parts)


def _evidence_type(onto: Any, kind: str) -> str:
    for e in onto.evidence_kinds:
        if e["id"] == kind:
            return str(e.get("produces", "observation")).replace(" ", "_")
    return "observation"


def _slug(text: str) -> str:
    return "".join(c if c.isalnum() else "-" for c in text).strip("-").lower()


def _origin(root: Path) -> str:
    return _git(root, "remote", "get-url", "origin") or "local"


def export(root: str | Path, group: str = "", project: str = "",
           project_dir: str | Path | None = None,
           out: str | Path | None = None) -> Path:
    m = build_manifest(root, group, project, project_dir)
    if out:
        path = Path(out)
    elif project_dir:
        path = Path(project_dir) / "governance" / "otop.json"
    else:
        path = Path(root) / "platform" / "src" / "pf" / "ontology" / "otop.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(m, indent=2) + "\n")
    return path


def stats(m: dict[str, Any]) -> dict[str, int]:
    by_kind: dict[str, int] = {}
    for o in m["objects"]:
        by_kind[o["kind"]] = by_kind.get(o["kind"], 0) + 1
    by_result: dict[str, int] = {}
    for o in m["objects"]:
        if o["kind"] == "evidence":
            by_result[o["result"]] = by_result.get(o["result"], 0) + 1
    return {**by_kind, "relationships": len(m["relationships"]),
            **{f"evidence_{k}": v for k, v in by_result.items()}}
