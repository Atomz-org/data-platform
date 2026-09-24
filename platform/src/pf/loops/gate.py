"""Path gating — the mechanical half of loop safety.

Rules an agent has to *remember* get skipped. This module is what the pre-commit
hook and the PreToolUse hook call, so a denied path is denied whether or not the
agent read the constraints file.

## Where the gate is enforced

Three times, over one rule read from one file:

  1. `.git/hooks/pre-commit`, over the staged set, before the commit exists.
  2. `.git/hooks/pre-push`, over every commit being pushed, before a pull
     request exists.
  3. `agent-context.yml`, over the commits a pull request adds, before it
     merges.

Only the first of those existed, and what followed was not hypothetical.
`maxFiles` is a *per-run* cap that `check_paths` applies to whatever set one
call hands it; the hook was the only caller; so everything that skips the hook
skipped the cap with it, silently. `git commit --no-verify` skips it. A fresh
clone has no hooks at all — git does not clone `.git/hooks` — which is how the
only code path that enforced `maxFiles` went uninvoked for the life of the
repo while the policy read as configured, and a 21-file commit landed
unchecked. Nothing downstream re-measured: the one place CI ran the gate over
a pull request was `claude-review.yml`, piped `|| true` into a context file for
a reviewer to read.

Layers 2 and 3 re-apply the *same* rule rather than inventing a stricter one.
`check_commits` measures each commit's own `ACMR` file list — exactly what the
hook would have staged and counted — so a commit that passed locally passes
again, and one that never met a hook is measured for the first time. The union
of a pull request is deliberately still uncapped; `pf.pr` says why.

An over-cap commit remains possible, and that is deliberate. A `Gate-Exempt:`
trailer turns the refusal into a warning that quotes its reason into the CI log
and the review. The rule was never that a change may not exceed twelve files.
It is that exceeding it may not be *silent* — which is precisely what
`--no-verify` and a missing hook made it.

Installing the hooks is therefore load-bearing rather than a nicety, and it is
the part that failed. `just hooks` has always been able to install them; nobody
ran it. A control that depends on a person remembering a setup step is the same
class of control as a rule an agent has to remember, so installation is now
something the platform does and checks: `pf bootstrap` installs them, the CLI
callback fills an empty slot on any command, `pf check` reports one missing, and
`pf install-hook` is the direct route. `install_hook` refuses to overwrite a
hook it did not write — silently replacing someone's own script would be a worse
failure than the one being fixed.
"""

from __future__ import annotations

import fnmatch
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml

Verdict = Literal["allow", "warn", "deny"]

#: The gate's own hooks: git's name for each, and the tracked script behind it.
#: Both read `gate.yaml`, so this is one rule applied at two moments rather than
#: two rules that can drift apart.
HOOKS: dict[str, str] = {
    "pre-commit": "platform/hooks/pre_commit.sh",
    "pre-push": "platform/hooks/pre_push.sh",
}

#: What each one is the last chance to catch. A hook whose purpose nobody can
#: state is a hook nobody reinstalls, so the missing-hook message says it.
_HOOK_WHY = {
    "pre-commit": "the gate does not run on commit",
    "pre-push": "a commit made with --no-verify leaves the machine unmeasured",
}

#: The pre-commit pair by name: most callers mean *the* hook, and these keep
#: reading the way they did before there were two.
HOOK_SOURCE = HOOKS["pre-commit"]
HOOK_TARGET = ".git/hooks/pre-commit"
#: Relative link target, from `.git/hooks/` back to the repo root. A relative
#: symlink keeps working when the checkout is moved or cloned to another path;
#: an absolute one silently points at the previous machine's directory.
HOOK_LINK = "../../platform/hooks/pre_commit.sh"

HookState = Literal["ok", "missing", "foreign", "no-git"]


def hooks_dir(root: Path) -> Path | None:
    """Where git will actually look for hooks here — `.git/hooks` is a guess.

    It is wrong in two real checkouts. In a linked worktree `.git` is a *file*
    naming the real git directory, so creating `.git/hooks` raises
    `NotADirectoryError` — which is how `pf bootstrap` died in every worktree,
    leaving the kind of checkout an agent is most likely to be working in with
    no gate at all. And `core.hooksPath` may move the directory anywhere.

    Asking git answers all three. `None` means git would not answer, which the
    callers read as "not a checkout".
    """
    proc = subprocess.run(
        ["git", "rev-parse", "--git-path", "hooks"], cwd=str(root), capture_output=True, text=True, check=False
    )
    if proc.returncode != 0 or not proc.stdout.strip():
        return None
    # Relative in an ordinary checkout, absolute from a worktree; both resolve.
    return (Path(root) / proc.stdout.strip()).resolve()


def _hook_link(hooks: Path, source_rel: str) -> str:
    """The relative symlink target, from the hooks directory to the script.

    Relative, so the link survives the checkout being moved or cloned to
    another path; an absolute one silently points at the previous machine's
    directory.

    Always resolved against the checkout that *owns* the hooks directory, and
    never against `root` when the two differ. Git keeps one hooks directory per
    repository and every worktree shares it, so a link into the worktree that
    happened to run the install is a link every *other* checkout then execs. It
    broke exactly that way: a worktree on a branch that added `pre_push.sh`
    installed the hook into the main checkout, whose branch predated the script
    — and every push from there ran a hook whose `pf gate --commits` its own
    `pf` had never heard of, so `git push` failed with a usage error until the
    link was deleted.

    Pointing at the owner's own path is right even when that file does not
    exist yet: git skips a hook it cannot execute, so the link lies dormant and
    starts working the moment that checkout has the script. `hook_status` reads
    a dangling link as `missing`, which is what it is.
    """
    return os.path.relpath(hooks.parent.parent / source_rel, hooks)


def _hook_sources(hooks: Path, root: Path, source_rel: str) -> set[Path]:
    """Every copy of the script that counts as ours.

    A worktree shares the main checkout's hooks directory, so the link there
    names the main checkout's script while `root` is the worktree's. Both are
    this repo's gate. Calling one of them foreign would report a missing gate
    in every worktree and then refuse to install one.
    """
    return {(Path(root) / source_rel).resolve(), (hooks.parent.parent / source_rel).resolve()}


def hook_status(root: Path, hook: str = "pre-commit") -> tuple[HookState, str]:
    """Is one of the gate's hooks actually installed?

    `foreign` is the case worth naming: a hook exists but is not ours. That is
    not "installed" and it is not "missing" — it is someone's own script that
    would be destroyed by a naive install, so it gets its own state and a
    refusal rather than being counted either way.
    """
    source = HOOKS[hook]
    hooks = hooks_dir(root)
    if hooks is None or not (Path(root) / ".git").exists():
        return "no-git", "not a git checkout — nothing to install into"

    target = hooks / hook
    if not target.exists() and not target.is_symlink():
        return "missing", f"no {hook} hook — {_HOOK_WHY[hook]}"

    # A link to nothing is not somebody's script to protect; it is an empty
    # slot that reads as occupied. Reported missing so `install_hook` replaces
    # it, rather than foreign — which would refuse, permanently, over a script
    # that is not there.
    if target.is_symlink() and not target.exists():
        if str(target.readlink()) == _hook_link(hooks, source):
            # Name the checkout that owns the hooks directory, which in a
            # worktree is not the one asking.
            owner = hooks.parent.parent
            where = "this checkout" if owner == Path(root).resolve() else str(owner)
            return "missing", f"{hook} is linked, but {source} is not in {where} yet"
        return "missing", f"{hook} points at a file that is gone — {_HOOK_WHY[hook]}"

    # A symlink pointing at our script, however it was spelled (relative from
    # `just hooks`, absolute from an older install), counts as ours.
    if target.is_symlink():
        dest = target.readlink()
        resolved = (target.parent / dest).resolve() if not dest.is_absolute() else dest
        if resolved in _hook_sources(hooks, root, source):
            return "ok", f"symlink → {source}"
        return "foreign", f"{hook} is a symlink to {dest}, not the platform gate"

    # A regular file that execs our script (someone chained it) also counts.
    try:
        body = target.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return "foreign", f"{hook} exists but is unreadable: {exc}"
    if source in body or "pf gate" in body:
        return "ok", f"{hook} calls the platform gate"
    return "foreign", f"{hook} exists and does not call the platform gate"


def install_hook(root: Path, *, force: bool = False, hook: str = "pre-commit") -> tuple[bool, str]:
    """Install one gate hook. Idempotent; never clobbers a foreign hook.

    Returns (changed, detail) — `changed` is False both when it was already
    installed and when installation was refused, so callers report the detail
    rather than inferring success from a boolean.
    """
    source_rel = HOOKS[hook]
    state, detail = hook_status(root, hook)
    if state == "no-git":
        return False, detail
    if state == "ok":
        return False, f"already installed ({detail})"

    source = Path(root) / source_rel
    if not source.exists():
        return False, f"{source_rel} is missing — nothing to install"

    hooks = hooks_dir(root)
    if hooks is None:
        return False, "git will not say where it looks for hooks — nothing to install into"

    target = hooks / hook
    link = _hook_link(hooks, source_rel)
    # Already pointing where it should, at a script this checkout does not carry
    # yet. Rewriting an identical link changes nothing and reports `changed`,
    # which made every `pf` command print "pre-push gate installed" on stderr
    # for as long as the state lasted.
    if target.is_symlink() and str(target.readlink()) == link:
        return False, f"already linked → {source_rel}, which this checkout does not carry yet"

    if state == "foreign" and not force:
        return False, (f"refused: {detail}. Move or chain it, then re-run — or pass force to replace it.")

    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() or target.is_symlink():
        target.unlink()
    target.symlink_to(link)
    # The hook is exec'd by git, so the *script* must be executable. The symlink
    # itself carries no mode of its own.
    source.chmod(source.stat().st_mode | 0o111)
    here = Path(root).resolve()
    shown = target.relative_to(here) if target.is_relative_to(here) else target
    return True, f"installed {shown} → {source_rel}"


def hooks_status(root: Path) -> list[tuple[str, HookState, str]]:
    """Every gate hook and whether it is in place, in installation order."""
    return [(hook, *hook_status(root, hook)) for hook in HOOKS]


def install_hooks(root: Path, *, force: bool = False) -> list[tuple[str, bool, str]]:
    """Install all of them. One refusal never stops the others being installed.

    A checkout with pre-commit chained into someone's own script and no
    pre-push at all is a real state, and the half that can be fixed should be.
    """
    return [(hook, *install_hook(root, force=force, hook=hook)) for hook in HOOKS]


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
        policy = yaml.safe_load(base.read_text(encoding="utf-8")) or {}

    extra_path = root / "gate.capabilities.yaml"
    if extra_path.exists():
        extra = yaml.safe_load(extra_path.read_text(encoding="utf-8")) or {}
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
        if (
            fnmatch.fnmatch(p, pat)
            or fnmatch.fnmatch(p, pat.replace("**/", ""))
            or fnmatch.fnmatch(Path(p).name, pat.replace("**/", ""))
        ):
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
        return GateResult("deny", f"denylist:{hit}", path, "generated artefact or secret — never edited by hand")

    if in_project:
        hit = _match(path, policy.get("platform_denylist", []))
        if hit:
            return GateResult(
                "deny",
                f"platform_denylist:{hit}",
                path,
                "shared platform infra; changing it from a project session affects every other company",
            )

    hit = _match(path, policy.get("autoMergeAllowlist", []))
    if hit:
        return GateResult("allow", f"allowlist:{hit}", path, "")

    hit = _match(path, policy.get("impact_required", []))
    if hit:
        return GateResult("warn", f"impact_required:{hit}", path, "run impact analysis before changing this")

    return GateResult("allow", "default", path, "")


def check_paths(
    paths: list[str], root: Path, in_project: bool = False, added: list[str] | None = None
) -> list[GateResult]:
    """Every per-path verdict, then the rules that judge the run as a whole.

    `added` is the subset of `paths` that are new files, when the caller knows
    it (the pre-commit hook and the PR workflow do). `None` means unknown, and
    unknown is treated as new: a caller that cannot say whether a source file
    is new gets the strict reading, not the lenient one.
    """
    results = [check_path(p, root, in_project) for p in paths]
    policy = load_policy(root)
    limit = int(policy.get("maxFiles", 0) or 0)
    if limit and len(paths) > limit:
        results.append(
            GateResult(
                "deny",
                f"maxFiles:{limit}",
                f"{len(paths)} files",
                f"a single run may touch at most {limit} files; split the change",
            )
        )
    results.extend(check_evidence(paths, root, added))
    results.extend(check_record_immutability(paths, root, added))
    results.extend(check_harness(paths, root))
    return results


# --------------------------------------------------- the cap, re-applied ----
#
# `check_paths` above is the cap at the moment of a commit. Everything below is
# the same cap at the two moments after it, because the first one is skippable
# and leaves no trace when it is skipped.

#: A commit message trailer that admits an over-cap commit, with its reason.
#:
#: `--no-verify` and an uninstalled hook both produce a commit the gate never
#: saw, and neither records that it happened. This does the opposite: the
#: commit says why it is large, in its own message, where review reads it and
#: `git log` keeps it. A bare `Gate-Exempt:` with nothing after it is not a
#: reason and does not exempt anything.
EXEMPT_TRAILER = "Gate-Exempt"
_EXEMPT_RE = re.compile(rf"^{EXEMPT_TRAILER}:[ \t]*(\S.*?)[ \t]*$", re.MULTILINE | re.IGNORECASE)


class GitError(RuntimeError):
    """git refused a command the commit check depends on.

    Raised rather than swallowed. A range that does not resolve — an unfetched
    base, a shallow clone — would otherwise select no commits and read exactly
    like a branch where every commit is within the cap, which is the one answer
    this check must never give by accident.
    """


def _git(root: Path, *args: str) -> str:
    proc = subprocess.run(["git", *args], cwd=str(root), capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise GitError(f"git {' '.join(args)}: {proc.stderr.strip() or f'exit {proc.returncode}'}")
    return proc.stdout


def commits_in(root: Path, spec: list[str]) -> list[str]:
    """The non-merge commits a rev-list spec selects, oldest first.

    Merges are excluded, and not for convenience: a merge's first-parent diff
    is every file the branch it absorbs ever touched, so capping it would
    refuse every merge while saying nothing about the commits inside — each of
    which is selected here in its own right and judged on its own files.
    """
    out = _git(root, "rev-list", "--no-merges", "--reverse", *spec)
    return [line.strip() for line in out.splitlines() if line.strip()]


def commit_files(root: Path, sha: str) -> list[str]:
    """What one commit added, copied, modified or renamed.

    The same `--diff-filter=ACMR` the pre-commit hook stages with, so this
    counts what that hook would have counted: deletions excluded (see the note
    in `gate.yaml`), a rename counted once, at its destination. `--root` so the
    first commit in a repository is measured rather than skipped for having no
    parent.
    """
    out = _git(root, "diff-tree", "--no-commit-id", "--name-only", "-r", "--root", "--diff-filter=ACMR", sha)
    return [line.strip() for line in out.splitlines() if line.strip()]


def commit_exemption(root: Path, sha: str) -> str:
    """The reason a commit gives for exceeding the cap, or "" if it gives none."""
    hit = _EXEMPT_RE.search(_git(root, "log", "-1", "--format=%B", sha))
    return hit.group(1).strip() if hit else ""


def check_commits(root: Path, spec: list[str]) -> list[GateResult]:
    """Re-apply `maxFiles` to each commit a rev-list spec selects.

    One result per commit that exceeds the cap, and nothing at all for the ones
    that do not — a clean range prints one line, not a hundred.

    Per commit, never over the union. A pull request legitimately touches more
    files than a single run should, which is why `pf pr report` skips the cap
    entirely; judging the union here would make every real pull request fail
    for the wrong reason, and the reason people would then remember is that the
    cap is noise.
    """
    limit = int(load_policy(root).get("maxFiles", 0) or 0)
    if not limit:
        return []
    out: list[GateResult] = []
    for sha in commits_in(root, spec):
        files = commit_files(root, sha)
        if len(files) <= limit:
            continue
        subject = _git(root, "log", "-1", "--format=%s", sha).strip()
        why = commit_exemption(root, sha)
        out.append(
            GateResult(
                "warn" if why else "deny",
                f"maxFiles:{limit}",
                f"{sha[:12]} {subject}",
                f"{len(files)} files — exempt: {why}"
                if why
                else f"{len(files)} files; a commit may touch at most {limit}. Split it, or record "
                f"why it cannot be split in a `{EXEMPT_TRAILER}: <reason>` trailer",
            )
        )
    return out


def _norm(p: str) -> str:
    return p.replace("\\", "/").removeprefix("./")


def _glob(path: str, pattern: str) -> bool:
    # `**/` is not fnmatch's; `*` already crosses `/`. Same reading as
    # `pf.evals.gate`, so a path the evals gate calls a skill this one does too.
    return fnmatch.fnmatch(path, pattern) or fnmatch.fnmatch(path, pattern.replace("**/", ""))


def _same_scope(a: str, b: str, n: int) -> bool:
    return n <= 0 or a.split("/")[:n] == b.split("/")[:n]


def check_evidence(paths: list[str], root: Path, added: list[str] | None = None) -> list[GateResult]:
    """A feature and its evidence land together — `gate.yaml`'s `tests_required`.

    For each pair, every path matching `source` must be accompanied, in the
    same run, by a path matching `evidence` within the same `scope`. A new
    source path with none is denied; a modified one is warned. One result per
    uncovered source path, so the message names the file and not the rule.

    The gate sees added, modified and renamed paths and never deleted ones, so
    a removed test is not evidence — which is the one way a rule like this is
    usually gamed. What it cannot judge is whether the evidence is real; a test
    that passes on the old code satisfies the pair and proves nothing. That is
    review's to keep, and `AGENTS.md` §4 says so.
    """
    policy = load_policy(root)
    pairs = [x for x in (policy.get("tests_required") or []) if isinstance(x, dict)]
    if not pairs:
        return []
    norm = [_norm(p) for p in paths]
    new = None if added is None else {_norm(p) for p in added}
    out: list[GateResult] = []
    for pair in pairs:
        src = str(pair.get("source") or "")
        ev = str(pair.get("evidence") or "")
        scope = int(pair.get("scope") or 0)
        if not src or not ev:
            continue
        hits = [p for p in norm if _glob(p, src)]
        if not hits:
            continue
        evidence = [p for p in norm if _glob(p, ev)]
        for h in hits:
            if any(_same_scope(h, e, scope) for e in evidence):
                continue
            is_new = new is None or h in new
            where = ev if scope <= 0 else f"{ev} under {'/'.join(h.split('/')[:scope])}"
            out.append(
                GateResult(
                    "deny" if is_new else "warn",
                    f"tests_required:{src}",
                    h,
                    f"{'added' if is_new else 'changed'} with nothing under {where} — "
                    f"a feature lands with the test or eval that proves it",
                )
            )
    return out


def _body_without_status(text: str) -> list[str]:
    """Every line of a record except the one that carries its status."""
    return [ln for ln in text.splitlines() if not ln.lstrip().startswith("**Status:**")]


def _is_accepted(text: str) -> bool:
    for ln in text.splitlines():
        if ln.lstrip().startswith("**Status:**"):
            return "accepted" in ln.split("**Status:**", 1)[1].split("·")[0].lower()
    return False


def check_record_immutability(
    paths: list[str], root: Path, added: list[str] | None = None
) -> list[GateResult]:
    """An accepted decision is corrected by adding a record, not by editing one.

    `decisions/README.md` has always said "Never delete one; supersede it", and
    until now nothing enforced it. An edited decision is worse than a missing
    one: the log still reads as a record of what was decided while no longer
    being one, and the review that was supposed to catch the change has no old
    text left to diff against.

    Three things are deliberately not refused. A record being drafted — one
    whose Status does not yet read `accepted` — is still being written. The
    Status line itself is exempt, because marking a record superseded is how a
    correction is meant to land. And a record git has never seen is an addition,
    not an edit.

    The comparison is against the index, not HEAD, for the same reason
    `_map_state` is: the index is what the commit will carry.
    """
    policy = load_policy(root)
    patterns = [p for p in (policy.get("records_immutable") or []) if isinstance(p, str)]
    if not patterns:
        return []
    new = None if added is None else {_norm(p) for p in added}
    out: list[GateResult] = []
    for raw in paths:
        rel = _norm(raw)
        if not any(_glob(rel, pat) for pat in patterns):
            continue
        if new is not None and rel in new:
            continue
        try:
            before = _git(root, "show", f"HEAD:{rel}")
        except GitError:
            # Not in HEAD: an addition, whatever the caller said. git is the
            # authority here, because a caller that mis-reports a new file as
            # modified would otherwise freeze a record that has no old text.
            continue
        if not before.strip():
            continue
        if not _is_accepted(before):
            continue
        after_path = root / rel
        try:
            after = after_path.read_text(encoding="utf-8")
        except OSError:
            continue
        if _body_without_status(before) == _body_without_status(after):
            continue
        out.append(
            GateResult(
                "deny",
                "records_immutable",
                rel,
                "an accepted decision was edited — correct it by adding a new "
                "record that supersedes this one, and change only its Status line here",
            )
        )
    return out


_SCOPE = re.compile(r"^groups/([^/]+)(?:/projects/([^/]+))?(?:/|$)")


def _map_state(root: Path, rel: str) -> str:
    """How git holds a map: `staged` (the index has what the tree has), `unstaged`
    (the tree moved past the index), `untracked`, or `unknown` outside a repo.

    The index, not HEAD, because the index is what the commit will carry: a map
    added for the first time is `staged` the moment it is, and a map that was
    regenerated after `git add` is `unstaged` even though HEAD never had it.
    """
    listed = subprocess.run(
        ["git", "ls-files", "--cached", "--", rel], cwd=str(root), capture_output=True, text=True, check=False
    )
    if listed.returncode != 0:
        return "unknown"
    if not listed.stdout.strip():
        return "untracked"
    diff = subprocess.run(
        ["git", "diff", "--quiet", "--", rel], cwd=str(root), capture_output=True, text=True, check=False
    )
    return {0: "staged", 1: "unstaged"}.get(diff.returncode, "unknown")


def check_harness(paths: list[str], root: Path) -> list[GateResult]:
    """A change to a scope lands with its harness map current — `gate.yaml`'s `harness_required`.

    For each changed path, the first entry whose `scope` matches names the maps
    the change can alter. Each such map is rendered from the tree as it stands
    and compared with the file: a missing or differing map is denied, and the
    message names the verb that regenerates it. A map that is current but
    differs from HEAD and is not in this run is denied too — it was regenerated
    and not staged, and the commit would lack it. Outside a repository the
    second half is unknown and is not judged.

    Currency, never presence: a change that leaves a map identical needs
    nothing in the run, which is what keeps this from being one more file to
    remember. What it cannot see is unstaged work beside the staged change —
    the tree is rendered as it is — and `pf harness check` in CI is the final
    word on the commit as committed.
    """
    policy = load_policy(root)
    rules = [x for x in (policy.get("harness_required") or []) if isinstance(x, dict)]
    if not rules:
        return []
    try:
        from pf import harnessmap
    except Exception:  # noqa: BLE001 — a gate must not fail closed on an import
        return []
    norm = [_norm(p) for p in paths]
    reached: dict[str, str] = {}
    for p in norm:
        rule = next((r for r in rules if _glob(p, str(r.get("scope") or ""))), None)
        if rule is None:
            continue
        m = _SCOPE.match(p)
        group, project = (m.group(1), m.group(2) or "") if m else ("", "")
        for template in rule.get("maps") or []:
            rel = str(template)
            if "{project}" in rel and not project:
                continue
            rel = rel.replace("{group}", group).replace("{project}", project)
            if "**" in rel:
                base = root / rel.split("**", 1)[0].rstrip("/")
                found = (
                    sorted(x.relative_to(root).as_posix() for x in base.rglob(harnessmap.FILE)) if base.is_dir() else []
                )
                for f in found:
                    reached.setdefault(f, p)
            else:
                reached.setdefault(rel, p)
    out: list[GateResult] = []
    for rel in sorted(reached):
        scope = harnessmap.scope_for(root, rel)
        if scope is None:
            continue  # a report map for a project that has no reporting/, say
        verb = f"pf harness {scope.group} {scope.project}".rstrip()
        path = root / rel
        if not path.is_file() or path.read_text(encoding="utf-8") != scope.render(root):
            out.append(
                GateResult(
                    "deny",
                    f"harness_required:{scope.label}",
                    rel,
                    f"stale against {reached[rel]} — a change to a scope lands with its harness map; "
                    f"run `{verb}` and stage this file",
                )
            )
            continue
        if rel not in norm and _map_state(root, rel) in ("unstaged", "untracked"):
            out.append(
                GateResult(
                    "deny",
                    f"harness_required:{scope.label}",
                    rel,
                    f"regenerated for {reached[rel]} but not in this run — `git add {rel}`",
                )
            )
    return out


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
    proc = subprocess.run(["git", "ls-files"], cwd=str(root), capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        return []
    allowed = policy.get("denylist_except", []) or []
    out: list[GateResult] = []
    for path in proc.stdout.splitlines():
        if _match(path, allowed):
            continue
        hit = _match(path, _applicable(path, deny))
        if hit:
            out.append(
                GateResult(
                    "deny",
                    f"tracked:{hit}",
                    path,
                    "git is tracking a file the gate calls generated — "
                    "`git rm --cached` it and add the pattern to .gitignore",
                )
            )
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
