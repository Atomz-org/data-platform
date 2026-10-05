"""The action gate: may this role write this path, and does a person have to
say so first.

It does not replace `gate.yaml`. The path policy — secrets, generated
artefacts, `provenance/**`, `vendor/**`, the platform tree from a project
session — is `pf.loops.gate.check_path`, and it is consulted first, with the
project-session flag on, so nothing here can widen it. What this adds is the
part the path policy cannot express:

  * **roles** — which agent may write where, from the entity's resolved
    `aidf.yaml`. A role that is not declared may write nothing through the
    engine; a declared one may write only under its globs.
  * **elevation** — targets that need a person. A write there by a role
    outside `elevated.roles` is `hold`, not `deny`: recorded, blocked, and
    waiting for `pf provenance approve <action_id>`.
  * **immutable roots** — the files that define the gate itself, refused by
    name so that a future relaxation of `gate.yaml` cannot make them writable
    by accident.

Every answer is a `GateDecision` with the rule that produced it, because the
ledger records the rule and a refusal without a rule cannot be appealed.
"""

from __future__ import annotations

from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path, PurePosixPath

from pf.aidf.config import AidfConfig
from pf.loops.gate import check_path

#: Repo-relative prefixes and files no agent writes through this engine, ever.
#: `provenance/` and `.github/` are also in gate.yaml; they are repeated here so
#: that the engine's answer does not depend on which of the two files a future
#: edit relaxes.
IMMUTABLE_ROOTS: tuple[str, ...] = (
    "provenance/", ".github/", "vendor/", "platform/",
    "gate.yaml", "gate.capabilities.yaml", "loop-constraints.md", "LOOP.md",
    "pyproject.toml", "uv.lock", "AGENTS.md", "CLAUDE.md",
)

Verdict = str  # "allow" | "warn" | "deny" | "hold"


class ActionGatePolicyViolation(PermissionError):
    """A write the gate refused. Carries the decision so the caller can log it."""

    def __init__(self, decision: GateDecision) -> None:
        super().__init__(f"{decision.rule}: {decision.message} ({decision.path})")
        self.decision = decision


@dataclass(frozen=True)
class GateDecision:
    verdict: Verdict
    rule: str
    message: str
    path: str  # repo-relative

    @property
    def blocked(self) -> bool:
        return self.verdict in ("deny", "hold")

    def as_gate_tuple(self) -> tuple[str, str, str]:
        """What `pf.provenance.action(gate=...)` takes."""
        return self.verdict, self.rule, self.message


class ActionGate:
    def __init__(self, root: Path, group: str, project: str, config: AidfConfig) -> None:
        self.root = root
        self.group = group
        self.project = project
        self.config = config
        self.project_rel = PurePosixPath("groups") / group / "projects" / project

    # -- paths --------------------------------------------------------------
    def normalise(self, target: str) -> str | None:
        """A project-relative POSIX path, or None when the target escapes.

        An absolute path, a `..` segment or a path that resolves outside the
        project is not "denied"; it is not a project path at all, and treating
        it as one would let `../../gate.yaml` be judged as `gate.yaml` — which
        the immutable list catches, but only by luck.
        """
        p = PurePosixPath(str(target).replace("\\", "/"))
        if p.is_absolute() or any(part in ("..", "") for part in p.parts if part != p.anchor):
            return None
        return str(p)

    def repo_rel(self, target_rel: str) -> str:
        return str(self.project_rel / target_rel)

    # -- the decision ------------------------------------------------------
    def authorize(self, target: str, role: str) -> GateDecision:
        rel = self.normalise(target)
        if rel is None:
            return GateDecision("deny", "aidf:path_traversal", "target must be a relative path inside the project",
                                str(target))
        repo_path = self.repo_rel(rel)

        for immutable in IMMUTABLE_ROOTS:
            if repo_path.startswith(immutable) or rel.startswith(immutable):
                return GateDecision("deny", "aidf:immutable",
                                    f"`{immutable}` is never written by an agent", repo_path)

        # gate.yaml first, as a project session: whatever it denies, this denies.
        pr = check_path(repo_path, self.root, in_project=True)
        if pr.blocked:
            return GateDecision("deny", pr.rule, pr.message, repo_path)

        roles = self.config.roles
        if role not in roles:
            return GateDecision("deny", "aidf:role",
                                f"role `{role}` is not declared in this entity's aidf.yaml", repo_path)
        if not any(fnmatch(rel, g) or fnmatch(rel, g.rstrip("*").rstrip("/") + "/*") for g in roles[role]):
            return GateDecision("deny", "aidf:role",
                                f"role `{role}` may not write `{rel}` (allowed: {roles[role]})", repo_path)

        elevated = [g for g in self.config.elevated_paths if fnmatch(rel, g)]
        if elevated and role not in self.config.elevated_roles:
            return GateDecision("hold", "human_oversight",
                                f"`{rel}` matches elevated path {elevated[0]}; a person approves this write",
                                repo_path)

        if pr.verdict == "warn":
            return GateDecision("warn", pr.rule, pr.message, repo_path)
        return GateDecision("allow", "aidf:role", f"role `{role}` may write `{rel}`", repo_path)
