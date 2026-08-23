"""Path gating — the mechanical half of loop safety.

Rules an agent has to *remember* get skipped. This module is what the pre-commit
hook and the PreToolUse hook call, so a denied path is denied whether or not the
agent read the constraints file.

## Where the gate is enforced

At commit time, locally, by `.git/hooks/pre-commit` — before anything is pushed
or a pull request exists. That is the whole enforcement story for `maxFiles` and
the denylist over a *staged set*: CI does not re-apply the run cap, deliberately.

Which makes installing that hook load-bearing rather than a nicety, and it is
the part that failed. `just hooks` has always been able to install it; nobody
ran it, so for the entire life of the repo the only code path that enforces
`maxFiles` was never invoked, and a 21-file commit landed unchecked. A control
that depends on a person remembering a setup step is the same class of control
as a rule an agent has to remember.

So installation is now something the platform does and checks: `pf bootstrap`
installs it, `pf check` reports it missing, and `pf install-hook` is the direct
route. `install_hook` refuses to overwrite a hook it did not write — silently
replacing someone's own pre-commit script would be a worse failure than the one
being fixed.
"""

from __future__ import annotations

import fnmatch
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml

Verdict = Literal["allow", "warn", "deny"]

#: The gate's own pre-commit hook, and where git expects to find it.
HOOK_SOURCE = "platform/hooks/pre_commit.sh"
HOOK_TARGET = ".git/hooks/pre-commit"
#: Relative link target, from `.git/hooks/` back to the repo root. A relative
#: symlink keeps working when the checkout is moved or cloned to another path;
#: an absolute one silently points at the previous machine's directory.
HOOK_LINK = "../../platform/hooks/pre_commit.sh"

HookState = Literal["ok", "missing", "foreign", "no-git"]


def hook_status(root: Path) -> tuple[HookState, str]:
    """Is the gate's pre-commit hook actually installed?

    `foreign` is the case worth naming: a hook exists but is not ours. That is
    not "installed" and it is not "missing" — it is someone's own script that
    would be destroyed by a naive install, so it gets its own state and a
    refusal rather than being counted either way.
    """
    git_dir = Path(root) / ".git"
    if not git_dir.exists():
        return "no-git", "not a git checkout — nothing to install into"

    target = Path(root) / HOOK_TARGET
    if not target.exists() and not target.is_symlink():
        return "missing", "no pre-commit hook — the gate does not run on commit"

    # A symlink pointing at our script, however it was spelled (relative from
    # `just hooks`, absolute from an older install), counts as ours.
    if target.is_symlink():
        dest = target.readlink()
        resolved = (target.parent / dest).resolve() if not dest.is_absolute() else dest
        if resolved == (Path(root) / HOOK_SOURCE).resolve():
            return "ok", f"symlink → {HOOK_SOURCE}"
        return "foreign", f"pre-commit is a symlink to {dest}, not the platform gate"

    # A regular file that execs our script (someone chained it) also counts.
    try:
        body = target.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return "foreign", f"pre-commit exists but is unreadable: {exc}"
    if HOOK_SOURCE in body or "pf gate" in body:
        return "ok", "pre-commit calls the platform gate"
    return "foreign", "pre-commit exists and does not call the platform gate"


def install_hook(root: Path, *, force: bool = False) -> tuple[bool, str]:
    """Install the pre-commit gate. Idempotent; never clobbers a foreign hook.

    Returns (changed, detail) — `changed` is False both when it was already
    installed and when installation was refused, so callers report the detail
    rather than inferring success from a boolean.
    """
    state, detail = hook_status(root)
    if state == "no-git":
        return False, detail
    if state == "ok":
        return False, f"already installed ({detail})"

    source = Path(root) / HOOK_SOURCE
    if not source.exists():
        return False, f"{HOOK_SOURCE} is missing — nothing to install"

    target = Path(root) / HOOK_TARGET
    if state == "foreign" and not force:
        return False, (f"refused: {detail}. Move or chain it, then re-run — "
                       f"or pass force to replace it.")

    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() or target.is_symlink():
        target.unlink()
    target.symlink_to(HOOK_LINK)
    # The hook is exec'd by git, so the *script* must be executable. The symlink
    # itself carries no mode of its own.
    source.chmod(source.stat().st_mode | 0o111)
    return True, f"installed {HOOK_TARGET} → {HOOK_SOURCE}"


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


#: File types that cannot be a credential store, whatever they are called.
#:
#: Deliberately short. `.yml` is not here — Kubernetes secrets and Ansible vaults
#: are YAML — and neither is `.py`, `.json` or `.csv`, each of which really can
#: hold a key. SQL and Markdown cannot: one is a query, the other is prose.
_NEVER_A_SECRET = frozenset({".sql", ".md"})


def _is_name_heuristic(pattern: str) -> bool:
    """Whether a denylist pattern is a guess from a filename rather than a fact.

    `**/secrets.toml` names a file. `**/credentials/**` names a directory. Both
    are statements about a specific thing. `**/*_key*` is different in kind: it
    matches any filename containing `_key` anywhere, which is a heuristic for
    "this looks like it holds a credential" — and heuristics have false
    positives. It denied `surrogate_key_hash.sql`, an ordinary dbt macro, and
    would deny `dim_key_accounts.sql` in the next project.

    The distinction is structural, not a list to maintain: a pattern whose
    basename is wrapped in `*` matches a substring of a name, and that is what
    makes it a guess.
    """
    name = pattern.rsplit("/", 1)[-1]
    return len(name) > 2 and name.startswith("*") and name.endswith("*")


def _applicable(path: str, patterns: list[str]) -> list[str]:
    """Drop name heuristics that cannot be true of this kind of file.

    Only the guesses are dropped. Every exact path and directory rule still
    applies — a compiled `target/**/*.sql` stays denied, because that rule is
    about where the file is, not about what its name suggests.
    """
    if Path(path).suffix.lower() not in _NEVER_A_SECRET:
        return patterns
    return [p for p in patterns or [] if not _is_name_heuristic(p)]


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

    # Exceptions are checked first, and only against the denylist. `.env.*` has
    # to catch `.env.local` and `.env.production`; it also caught `.env.example`,
    # a committed template with no secret in it, which made the one file people
    # need to edit when adding a variable unwritable.
    if _match(path, policy.get("denylist_except", [])):
        return GateResult("allow", "denylist_except", path, "")

    hit = _match(path, _applicable(path, policy.get("denylist", [])))
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
                          capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        return []
    allowed = policy.get("denylist_except", []) or []
    out: list[GateResult] = []
    for path in proc.stdout.splitlines():
        if _match(path, allowed):
            continue
        hit = _match(path, _applicable(path, deny))
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
