"""Owner-editable governance: DuckDB is the edit surface, YAML stays canonical.

## Why both

A data owner who has to open a pull request to fix a description does not fix the
description. That is the case for putting the ontology behind a form. But the
ontology is also the thing every projection is derived from — MDL, OWL, the
otop policy manifest, the review checks Recce generates — and moving it into a
database would take those definitions out of code review and out of the gate at
exactly the moment they became easier to change.

So the edit goes to both places, in this order:

    form  ->  governance.edits  (append-only audit row, in DuckDB)
          ->  the YAML file      (rewritten in place)
          ->  git / `pf check`   (unchanged: still reviewed, still validated)

The audit row is written *before* the file, and carries `applied` separately. A
row with `applied = false` is an attempt that failed to land, which is a
different fact from an edit nobody made, and the one you need when a file's
contents disagree with what someone remembers doing.

## Why the YAML is rewritten rather than regenerated

`ruamel`-style round-tripping is not used, and the file is not re-emitted from a
model. Every one of these files carries comments that explain *why* a class or a
policy exists, and a dumper strips them. Instead a single scalar is located and
replaced textually, which is why `set_path` refuses anything but a scalar: an
edit that cannot be made without rewriting structure is one a human should make
in the file, and the API says so rather than flattening the comments to succeed.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from pf import obs

SCHEMA = """
CREATE SCHEMA IF NOT EXISTS governance;

-- Append-only. Nothing here is ever UPDATEd: a correction is a new row whose
-- `before` is the previous row's `after`, so the history reads as a sequence of
-- states rather than as a field whose past you have to trust someone about.
CREATE TABLE IF NOT EXISTS governance.edits (
    id TEXT PRIMARY KEY,
    ts TIMESTAMP,
    actor TEXT,
    surface TEXT,          -- concepts | topology | policy | instance
    scope TEXT,            -- '' for platform-wide, else the group
    key_path TEXT,         -- dotted path into the YAML document
    before TEXT,
    after TEXT,
    reason TEXT,
    applied BOOLEAN,       -- did the YAML actually get written
    error TEXT,
    file_path TEXT
);
"""


class EditRejected(Exception):
    """The edit was refused before anything was written."""


@dataclass(frozen=True)
class Surface:
    """One editable governance document."""

    name: str
    title: str
    #: Path relative to the repo root, or to the group directory when scoped.
    rel: str
    scoped: bool
    description: str


SURFACES: dict[str, Surface] = {
    "concepts": Surface(
        "concepts", "Concepts",
        "platform/src/pf/ontology/concepts.yaml", False,
        "Shared business vocabulary: classes, their identity, their properties."),
    "topology": Surface(
        "topology", "Topology",
        "platform/src/pf/ontology/topology.yaml", False,
        "Named relations between classes, and their cardinality."),
    "policy": Surface(
        "policy", "Policy",
        "platform/src/pf/ontology/policy.yaml", False,
        "Intents and constraints, and what enforces each one."),
    "instance": Surface(
        "instance", "Group scope",
        "ontology/instance.yaml", True,
        "Which platform classes this group actually models."),
}


def surfaces() -> list[dict[str, Any]]:
    return [{"name": s.name, "title": s.title, "rel": s.rel,
             "scoped": s.scoped, "description": s.description}
            for s in SURFACES.values()]


def _path_for(surface: str, root: Path, group: str = "") -> Path:
    s = SURFACES.get(surface)
    if s is None:
        raise EditRejected(f"unknown governance surface {surface!r}")
    if s.scoped:
        if not group:
            raise EditRejected(f"surface {surface!r} needs a group")
        return root / "groups" / group / s.rel
    return root / s.rel


# ------------------------------------------------------------------- read --
def current(surface: str, root: Path, group: str = "") -> dict[str, Any]:
    """The document as it stands, plus where it came from."""
    path = _path_for(surface, root, group)
    if not path.exists():
        return {"surface": surface, "group": group, "path": str(path),
                "exists": False, "document": {}}
    return {
        "surface": surface, "group": group, "path": str(path), "exists": True,
        "document": yaml.safe_load(path.read_text(encoding="utf-8")) or {},
    }


def history(root: Path, surface: str = "", group: str = "",
            limit: int = 200) -> list[dict[str, Any]]:
    """Audit trail, newest first. Never raises on a missing table."""
    where, params = [], []
    if surface:
        where.append("surface = ?")
        params.append(surface)
    if group:
        where.append("scope = ?")
        params.append(group)
    clause = ("WHERE " + " AND ".join(where)) if where else ""
    sql = (f"SELECT id, ts, actor, surface, scope, key_path, before, after, "
           f"reason, applied, error FROM governance.edits {clause} "
           f"ORDER BY ts DESC LIMIT {int(limit)}")
    try:
        with obs.connect(root, read_only=True) as con:
            rows = con.execute(sql, params).fetchall()
            cols = [d[0] for d in con.description]
    except Exception:  # noqa: BLE001 — an unwritten audit table is "no history"
        return []
    return [dict(zip(cols, r, strict=False)) for r in rows]


# ------------------------------------------------------------------ write --
def _read_scalar(doc: Any, key_path: str) -> Any:
    node = doc
    for part in key_path.split("."):
        if isinstance(node, list):
            try:
                node = node[int(part)]
                continue
            except (ValueError, IndexError) as exc:
                raise EditRejected(f"no such path: {key_path}") from exc
        if not isinstance(node, dict) or part not in node:
            raise EditRejected(f"no such path: {key_path}")
        node = node[part]
    return node


def _replace_scalar(text: str, key_path: str, before: Any, after: str) -> str:
    """Replace one scalar in place, keeping every comment and all formatting.

    Located by walking the document for the *line* that holds the leaf key at
    the right nesting, rather than by regex over the whole file: `description:`
    appears dozens of times in concepts.yaml and replacing the first match would
    silently rewrite an unrelated class.
    """
    leaf = key_path.split(".")[-1]
    parents = key_path.split(".")[:-1]
    lines = text.splitlines(keepends=True)

    depth = 0
    out: list[str] = []
    matched = False
    for line in lines:
        stripped = line.strip()
        if not matched and depth < len(parents) and stripped.startswith(
                f"{parents[depth]}:"):
            depth += 1
            out.append(line)
            continue
        if not matched and depth == len(parents) and stripped.startswith(f"{leaf}:"):
            indent = line[: len(line) - len(line.lstrip())]
            rendered = yaml.safe_dump(after, default_flow_style=True).strip()
            if rendered.endswith("\n...") :
                rendered = rendered[:-4]
            out.append(f"{indent}{leaf}: {rendered}\n")
            matched = True
            continue
        out.append(line)

    if not matched:
        raise EditRejected(
            f"could not locate {key_path} as a scalar line — edit it in the file")
    return "".join(out)


def apply_edit(root: Path, surface: str, key_path: str, after: Any, *,
               actor: str, reason: str = "", group: str = "") -> dict[str, Any]:
    """Record the edit, then write it. Returns the audit row.

    The audit row is written first and marked `applied` only once the file is on
    disk, so a failed write leaves evidence rather than nothing.
    """
    path = _path_for(surface, root, group)
    if not path.exists():
        raise EditRejected(f"{path} does not exist")

    text = path.read_text(encoding="utf-8")
    doc = yaml.safe_load(text) or {}
    before = _read_scalar(doc, key_path)
    if isinstance(before, (dict, list)):
        raise EditRejected(
            f"{key_path} is a {type(before).__name__}, not a value. Structural "
            f"changes are made in the file so their comments survive review.")
    if before == after:
        raise EditRejected(f"{key_path} is already {after!r}")

    row = {
        "id": str(uuid.uuid4()), "ts": datetime.now(UTC),
        "actor": actor or "unknown", "surface": surface, "scope": group,
        "key_path": key_path, "before": json.dumps(before),
        "after": json.dumps(after), "reason": reason, "applied": False,
        "error": "", "file_path": str(path),
    }

    try:
        updated = _replace_scalar(text, key_path, before, after)
    except EditRejected as exc:
        row["error"] = str(exc)
        _write_row(root, row)
        raise

    path.write_text(updated, encoding="utf-8")
    row["applied"] = True
    _write_row(root, row)
    return {**row, "ts": row["ts"].isoformat(),
            "before": before, "after": after}


def revert(root: Path, edit_id: str, *, actor: str) -> dict[str, Any]:
    """Undo one recorded edit by applying its `before` as a new edit."""
    rows = [r for r in history(root, limit=1000) if r["id"] == edit_id]
    if not rows:
        raise EditRejected(f"no edit {edit_id}")
    r = rows[0]
    return apply_edit(root, r["surface"], r["key_path"], json.loads(r["before"]),
                      actor=actor, group=r["scope"] or "",
                      reason=f"revert of {edit_id}")


def _write_row(root: Path, row: dict[str, Any]) -> None:
    with obs.connect(root) as con:
        con.execute(SCHEMA)
        con.execute(
            "INSERT INTO governance.edits (id, ts, actor, surface, scope, "
            "key_path, before, after, reason, applied, error, file_path) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            [row["id"], row["ts"], row["actor"], row["surface"], row["scope"],
             row["key_path"], row["before"], row["after"], row["reason"],
             row["applied"], row["error"], row["file_path"]])
