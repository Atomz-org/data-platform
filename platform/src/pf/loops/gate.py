"""Path gating — the mechanical half of loop safety.

Rules an agent has to *remember* get skipped. This module is what the pre-commit
hook and the PreToolUse hook call, so a denied path is denied whether or not the
agent read the constraints file.
"""

from __future__ import annotations

import fnmatch
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml

Verdict = Literal["allow", "warn", "deny"]


@dataclass(frozen=True)
class GateResult:
    verdict: Verdict
    rule: str
    path: str
    message: str

    @property
    def blocked(self) -> bool:
        return self.verdict == "deny"


def load_policy(root: Path) -> dict[str, Any]:
    """The hand-written policy, unioned with capability-contributed rules.

    Two files rather than one so that installing a capability never rewrites
    `gate.yaml`: a YAML round-trip would silently drop every comment in it, and
    the comments are where the *reasons* for each rule live. Capabilities may
    only add patterns — the merge appends, so nothing installable can loosen the
    gate that judges it.
    """
    policy: dict[str, Any] = {}
    base = root / "gate.yaml"
    if base.exists():
        policy = yaml.safe_load(base.read_text()) or {}

    extra_path = root / "gate.capabilities.yaml"
    if extra_path.exists():
        extra = yaml.safe_load(extra_path.read_text()) or {}
        for section, patterns in extra.items():
            if not isinstance(patterns, list):
                continue
            bucket = policy.setdefault(section, [])
            bucket.extend(p for p in patterns if p not in bucket)
    return policy


def _match(path: str, patterns: list[str]) -> str | None:
    # `removeprefix`, not `lstrip("./")`: lstrip strips a *character set*, so it
    # ate the leading dot of ".env" and turned a denylisted secret into "env",
    # which matched nothing. Dotfiles at the repo root were silently writable.
    p = path.replace("\\", "/").removeprefix("./")
    for pat in patterns or []:
        # fnmatch does not treat ** specially; compare against both the full path
        # and the bare filename so "**/x" and "x" both behave as expected.
        if fnmatch.fnmatch(p, pat) or fnmatch.fnmatch(p, pat.replace("**/", "")) \
           or fnmatch.fnmatch(Path(p).name, pat.replace("**/", "")):
            return pat
    return None


def check_path(path: str, root: Path, in_project: bool = False) -> GateResult:
    """Classify one path against the policy."""
    policy = load_policy(root)

    hit = _match(path, policy.get("denylist", []))
    if hit:
        return GateResult("deny", f"denylist:{hit}", path,
                          "generated artefact or secret — never edited by hand")

    if in_project:
        hit = _match(path, policy.get("platform_denylist", []))
        if hit:
            return GateResult("deny", f"platform_denylist:{hit}", path,
                              "shared platform infra; changing it from a project "
                              "session affects every other company")

    hit = _match(path, policy.get("autoMergeAllowlist", []))
    if hit:
        return GateResult("allow", f"allowlist:{hit}", path, "")

    hit = _match(path, policy.get("impact_required", []))
    if hit:
        return GateResult("warn", f"impact_required:{hit}", path,
                          "run impact analysis before changing this")

    return GateResult("allow", "default", path, "")


def check_paths(paths: list[str], root: Path, in_project: bool = False) -> list[GateResult]:
    results = [check_path(p, root, in_project) for p in paths]
    policy = load_policy(root)
    limit = int(policy.get("maxFiles", 0) or 0)
    if limit and len(paths) > limit:
        results.append(GateResult("deny", f"maxFiles:{limit}", f"{len(paths)} files",
                                  f"a single run may touch at most {limit} files; "
                                  f"split the change"))
    return results


def tracked_denied(root: Path) -> list[GateResult]:
    """Files git is tracking that the gate calls generated.

    The two policies were written independently and drifted, in the quietest
    possible way. `.gitignore` had `kg/*.duckdb`; because that pattern contains a
    slash, git anchors it to the repo root, so it never matched
    `groups/*/projects/*/kg/graph.duckdb`. The gate denied those paths the whole
    time — and git committed 1,622 of them, because nothing compared the two.

    Checking is the fix. A denylist entry that git ignores is a rule; one that
    git tracks is a rule with a counterexample sitting in the repository.
    """
    policy = load_policy(root)
    deny = policy.get("denylist", []) or []
    if not deny:
        return []
    proc = subprocess.run(["git", "ls-files"], cwd=str(root),
                          capture_output=True, text=True)
    if proc.returncode != 0:
        return []
    out: list[GateResult] = []
    for path in proc.stdout.splitlines():
        hit = _match(path, deny)
        if hit:
            out.append(GateResult(
                "deny", f"tracked:{hit}", path,
                "git is tracking a file the gate calls generated — "
                "`git rm --cached` it and add the pattern to .gitignore"))
    return out


def project_for(path: str, root: Path) -> tuple[str, str, Path] | None:
    """Resolve which group/project a path belongs to, if any."""
    p = (root / path).resolve() if not Path(path).is_absolute() else Path(path).resolve()
    for parent in [p, *p.parents]:
        if parent.parent.name == "projects" and (parent.parent.parent / "ontology").exists():
            return parent.parent.parent.name, parent.name, parent
    return None


def nodes_for(path: str) -> list[str]:
    """Graph node ids implied by a changed file."""
    p = Path(path)
    if p.suffix == ".sql" and "models" in p.parts:
        return [f"model:{p.stem}"]
    if p.suffix == ".py" and "sources" in p.parts:
        return [f"source:{p.stem}"]
    return []
