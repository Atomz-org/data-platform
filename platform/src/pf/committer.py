"""Commit segregation by a locally served model.

The session that implements logic is not the session that decides commit
boundaries. A local model — served off this machine's own weights, no tokens
spent, no code leaving the laptop — reads the working tree and proposes how it
splits into commits; this module is everything around that proposal that must
NOT be a model's opinion:

- the survey of what changed (git, deterministic),
- validation of the proposed split (every changed file assigned exactly once,
  nothing gate-denied, nothing under `vendor/**` — a pin bump is a human
  decision, never a model's),
- the apply (ordinary `git commit`, so the pre-commit impact gate still fires),
- and the record (each commit is a provenance action; the message carries the
  model's name as a trailer, so attribution survives in history).

The model only ever produces a *plan* — JSON naming groups of files and a
message for each. It runs no git command and touches no file; a hallucinated
path is a validation error, not a staged change.

Backends: an OpenAI-compatible local server (`mlx_lm.server`, LM Studio,
Ollama's compat endpoint — `PF_COMMIT_LLM_URL` / `PF_COMMIT_LLM_MODEL`), with
headless `claude -p` as the fallback when the local server is not answering.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

# mlx_lm.server's default bind. LM Studio is :1234, Ollama's compat layer
# :11434/v1 — all take the same request body, so the URL is the whole switch.
DEFAULT_URL = "http://127.0.0.1:8080/v1/chat/completions"
DEFAULT_MODEL = "mlx-community/Qwen3.5-9B-MLX-4bit"

#: Per-file and whole-prompt budgets. Grouping is decided by paths, status
#: codes and a glimpse of content — not by whole diffs — and prefill speed on
#: a laptop-served model is the binding constraint (a 19k-token survey was
#: measured thrashing an 8 GB machine at ~7 tok/s). Past the budget, files are
#: presented as name and status only, which still groups correctly.
DIFF_CHARS_PER_FILE = 400
PROMPT_CHAR_BUDGET = 12_000

SUBJECT_MAX = 100


# ------------------------------------------------------------------ survey --
@dataclass(frozen=True)
class Change:
    status: str  # porcelain XY code, e.g. " M", "??", "A "
    path: str


def _git(root: Path, *args: str) -> str:
    out = subprocess.run(  # noqa: S603 — argv built here, nothing user-shaped
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return out.stdout


def changed_files(root: Path) -> list[Change]:
    """Every pending change, untracked files listed individually.

    `--no-renames` on purpose: a rename arrives as a delete plus an add, two
    plain paths the plan can carry, instead of a two-field record every layer
    downstream would need to understand. `--ignore-submodules=dirty` too:
    uncommitted churn *inside* a vendored checkout is not a change of ours and
    would deadlock every plan (unassignable, uncommittable).
    """
    lines = _git(root, "status", "--porcelain", "--no-renames", "--ignore-submodules=dirty", "-uall").splitlines()
    return [
        Change(status=ln[:2], path=ln[3:])
        for ln in lines
        # Never present the committer's own scratch plan, and never present the
        # provenance ledger — it is gitignored in a platform checkout, but this
        # holds even where it is not: the record of the commits must not ride
        # inside one of them. Vendored pin moves are filtered too: the tool
        # refuses to commit them (a bump is a human decision), so presenting
        # one would deadlock every full-tree plan — the pin stays pending in
        # the tree, visible to `git status`, for a person to bump or restore.
        if len(ln) > 3
        and ln[3:] != "data/commit_plan.json"
        and not ln[3:].startswith(("provenance/", "vendor/"))
        and ln[3:] != ".gitmodules"
    ]


def tree_fingerprint(root: Path) -> str:
    """Identity of the working tree a plan was made for.

    Status codes and paths only — enough that any commit, edit or new file
    invalidates a saved plan, cheap enough to run on every `--apply`. Derived
    from `changed_files`, not raw status, so writing the plan file itself does
    not invalidate the plan it holds.
    """
    raw = "".join(f"{c.status} {c.path}\n" for c in changed_files(root))
    return hashlib.sha256(raw.encode()).hexdigest()


def _excerpt(root: Path, change: Change) -> str:
    if change.status == "??":
        try:
            text = (root / change.path).read_text(errors="replace")
        except OSError:
            return "(unreadable)"
        if "\x00" in text[:DIFF_CHARS_PER_FILE]:
            return "(binary — content elided)"
        return text[:DIFF_CHARS_PER_FILE]
    try:
        diff = _git(root, "diff", "HEAD", "--no-color", "--", change.path)
    except subprocess.CalledProcessError:
        return "(no diff)"
    return diff[:DIFF_CHARS_PER_FILE]


def survey(root: Path, changes: list[Change]) -> str:
    """The working tree as the model will see it, inside the prompt budget."""
    blocks: list[str] = []
    spent = 0
    for c in changes:
        if spent < PROMPT_CHAR_BUDGET:
            body = _excerpt(root, c)
            spent += len(body)
            blocks.append(f"--- {c.status} {c.path}\n{body}")
        else:
            blocks.append(f"--- {c.status} {c.path}\n(diff elided — over prompt budget)")
    return "\n".join(blocks)


# ------------------------------------------------------------------- plan ---
@dataclass
class PlannedCommit:
    message: str
    files: list[str] = field(default_factory=list)

    @property
    def subject(self) -> str:
        return self.message.splitlines()[0].strip() if self.message.strip() else ""


PROMPT = """You segregate a git working tree into logical commits.

Rules:
- Group files by concern: one commit per coherent change, platform vs project \
work never mixed, generated artefacts ride with the change that regenerated them.
- Every listed file must appear in exactly one commit. Never invent a path.
- Plan ONLY the changed files listed below. Do not restate commits from the \
history — it is style reference, not work to redo. A commit with no files is invalid.
- Subject line in the style of the recent history below: imperative, \
`scope: what changed` where the history does that, under {subject_max} chars. \
A body is welcome when the why is not obvious.
- Answer with ONLY this JSON, no prose around it:
  {{"commits": [{{"message": "...", "files": ["path", ...]}}]}}
{style}
Recent commit subjects of this repository:
{history}

Changed files and their diffs:
{survey}
"""

#: Where the curated commit conventions live, and how much of them the model
#: sees. A distilled guide (a NotebookLM briefing, a style doc — anything a
#: human curated) beats twelve log lines at teaching grouping and phrasing,
#: but prefill on a laptop-served model is the binding constraint, so it is
#: capped rather than trusted to be short.
STYLE_FILE = "docs/COMMIT-STYLE.md"
STYLE_CHARS_MAX = 2_500


def style_guide(root: Path) -> str:
    """The house commit conventions, if someone has written them down.

    `PF_COMMIT_STYLE_FILE` overrides the default location. Absent file, empty
    file, unreadable file — all mean no style section, never an error: the
    guide is an upgrade, not a dependency.
    """
    path = Path(os.environ.get("PF_COMMIT_STYLE_FILE", "") or root / STYLE_FILE)
    try:
        text = path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return ""
    if not text or "\x00" in text[:STYLE_CHARS_MAX]:
        return ""
    return text[:STYLE_CHARS_MAX]


def build_prompt(root: Path, changes: list[Change]) -> str:
    history = _git(root, "log", "--format=%s", "-12")
    style = style_guide(root)
    section = f"\nHouse commit conventions (authoritative for grouping and message style):\n{style}\n" if style else ""
    return PROMPT.format(subject_max=SUBJECT_MAX, style=section, history=history, survey=survey(root, changes))


def loads_reply(text: str) -> dict:
    """A model reply as a JSON object, tolerating the wrappings models add.

    Reasoning models wrap answers in think-blocks and chat models in code
    fences; both are stripped rather than forbidden, because the contract is
    the JSON, not the wrapping. One structural fault is repaired rather than
    bounced: a reply that simply stops before closing its brackets (measured:
    Qwen3.5-4B reliably drops the final `}`). Appending the missing closers
    is unambiguous — nothing after them could have meant anything else — while
    any other malformation still raises for the repair round-trip.
    """
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
    candidate = fenced.group(1) if fenced else text[text.find("{") :].rstrip()
    try:
        # raw_decode: the first JSON value, trailing prose ignored.
        return json.JSONDecoder().raw_decode(candidate)[0]
    except (json.JSONDecodeError, ValueError) as exc:
        stack: list[str] = []
        in_string = escaped = False
        for ch in candidate:
            if escaped:
                escaped = False
            elif ch == "\\" and in_string:
                escaped = True
            elif ch == '"':
                in_string = not in_string
            elif not in_string and ch in "{[":
                stack.append("}" if ch == "{" else "]")
            elif not in_string and ch in "}]" and stack and stack[-1] == ch:
                stack.pop()
        if not stack:
            raise ValueError(f"model reply is not the declared JSON shape: {exc}") from exc
        try:
            return json.loads(candidate + ('"' if in_string else "") + "".join(reversed(stack)))
        except (json.JSONDecodeError, ValueError):
            raise ValueError(f"model reply is not the declared JSON shape: {exc}") from exc


def parse_plan(text: str) -> list[PlannedCommit]:
    """The model's reply, held to the declared shape."""
    doc = loads_reply(text)
    commits = doc.get("commits")
    if not isinstance(commits, list):
        raise ValueError("model reply has no 'commits' list")
    plan = [
        PlannedCommit(message=str(c.get("message", "")).strip(), files=[str(f) for f in c.get("files", [])])
        for c in commits
        if isinstance(c, dict)
    ]
    if not plan:
        raise ValueError("model proposed an empty plan")
    return plan


def drop_fileless(plan: list[PlannedCommit]) -> int:
    """Remove commits that name no files; return how many were dropped.

    Measured failure: given a small change set, the model pads its plan by
    echoing the recent-history subjects as file-less commits. A commit with
    no files can never stage anything, so dropping them is safe — and done
    before validation so one hallucination doesn't reject an otherwise
    complete plan. The count is surfaced, not hidden.
    """
    fileless = [p for p in plan if not p.files]
    plan[:] = [p for p in plan if p.files]
    return len(fileless)


SWEEP_SUBJECT = "chore: remaining changes the model left unassigned"


def complete_plan(plan: list[PlannedCommit], changes: list[Change]) -> list[str]:
    """Sweep unassigned changes into one labeled trailing commit.

    A small model reliably forgets a few files near the end of a long survey,
    and a fresh plan costs minutes of local inference. The remedy is
    deterministic rather than another roll of the dice: whatever the model did
    not place goes into one commit that says exactly that, so nothing is lost
    and nothing is misattributed to a concern it does not belong to. Returns
    the swept paths (empty when the model accounted for everything).
    """
    assigned = {f for p in plan for f in p.files}
    rest = sorted(c.path for c in changes if c.path not in assigned)
    if rest:
        plan.append(
            PlannedCommit(
                message=(
                    SWEEP_SUBJECT + "\n\nSwept deterministically by pf.committer after the model's plan\n"
                    "covered every other change but not these."
                ),
                files=rest,
            )
        )
    return rest


# -------------------------------------------------------------- validation --
def validate_plan(plan: list[PlannedCommit], changes: list[Change], root: Path) -> list[str]:
    """Everything that must be true before a single file is staged.

    The model proposes; this disposes. Each problem is returned, not raised,
    so the caller can show the whole verdict at once — a plan that fails three
    ways should not need three round trips to discover.
    """
    problems: list[str] = []
    changed = {c.path for c in changes}
    seen: dict[str, str] = {}

    for i, commit in enumerate(plan, 1):
        if not commit.subject:
            problems.append(f"commit {i}: empty message")
        elif len(commit.subject) > SUBJECT_MAX:
            problems.append(f"commit {i}: subject over {SUBJECT_MAX} chars")
        if not commit.files:
            problems.append(f"commit {i} ({commit.subject!r}): no files")
        for path in commit.files:
            if path not in changed:
                problems.append(f"commit {i}: {path} is not a pending change — invented path")
            if path in seen:
                problems.append(f"{path} assigned to both {seen[path]!r} and {commit.subject!r}")
            seen[path] = commit.subject
            if path.startswith("vendor/") or path == ".gitmodules":
                problems.append(f"{path}: a submodule pin bump is a human decision, never committed here")

    unassigned = sorted(changed - set(seen))
    for path in unassigned:
        problems.append(f"{path}: changed but assigned to no commit")

    try:
        from pf.loops.gate import check_path

        for path in sorted(set(seen)):
            verdict = check_path(path, root)
            if verdict.verdict == "deny":
                problems.append(f"{path}: gate-denied ({verdict.rule}) — refuse to stage")
    except FileNotFoundError:
        pass  # no gate.yaml — scratch repo; the git-level checks above still ran

    return problems


# ----------------------------------------------------------------- backends --
class LocalBackend:
    """An OpenAI-compatible completions server on this machine."""

    def __init__(self, url: str | None = None, model: str | None = None) -> None:
        self.url = url or os.environ.get("PF_COMMIT_LLM_URL", DEFAULT_URL)
        self.model = model or os.environ.get("PF_COMMIT_LLM_MODEL", DEFAULT_MODEL)
        self.name = self.model

    def complete(self, prompt: str) -> str:
        body = json.dumps(
            {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0,
                # Reasoning models spend tokens thinking before answering, and
                # a budget the thinking exhausts returns a message with no
                # content at all. Generous by default, and a knob because
                # "generous" is model-sized.
                "max_tokens": int(os.environ.get("PF_COMMIT_LLM_MAX_TOKENS", "12000")),
                "stream": False,
            }
        ).encode()
        req = urllib.request.Request(  # noqa: S310 — localhost completions endpoint
            self.url, data=body, headers={"Content-Type": "application/json"}
        )
        timeout = float(os.environ.get("PF_COMMIT_LLM_TIMEOUT", "180"))
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            reply = json.loads(resp.read())
        choice = reply["choices"][0]
        content = (choice.get("message", {}).get("content") or "").strip()
        if not content:
            raise ValueError(
                f"local model returned no answer (finish_reason="
                f"{choice.get('finish_reason')!r}) — it likely spent the whole "
                "token budget reasoning; raise PF_COMMIT_LLM_MAX_TOKENS"
            )
        return content


class ClaudeBackend:
    """Headless `claude -p`, the fallback when nothing local is serving."""

    def __init__(self, model: str = "haiku") -> None:
        self.model = model
        self.name = f"claude-{model}"

    def complete(self, prompt: str) -> str:
        # The prompt goes over stdin, not argv: diffs of binary files carry
        # NUL bytes no argv may hold, and a big tree overflows ARG_MAX anyway.
        out = subprocess.run(  # noqa: S603
            ["claude", "-p", "--model", self.model, "--output-format", "text"],
            input=prompt,
            capture_output=True,
            text=True,
            timeout=300,
        )
        if out.returncode != 0:
            # Auth problems surface here (a stale ANTHROPIC_API_KEY shadowing a
            # claude.ai login, say) — the CLI's own words beat "exit status 1".
            raise RuntimeError(f"claude -p failed: {out.stderr.strip()[-300:]}")
        return out.stdout


def backend(kind: str | None = None):
    """`local` unless told otherwise; `claude` only if the CLI exists."""
    kind = kind or os.environ.get("PF_COMMIT_BACKEND", "local")
    if kind == "claude":
        if not shutil.which("claude"):
            raise RuntimeError("claude CLI not on PATH")
        return ClaudeBackend()
    return LocalBackend()


def plan_with_fallback(prompt: str, kind: str | None = None):
    """One completion, from whichever backend is actually answering.

    A local server that is down is an everyday state, not an error worth a
    stack trace — fall through to the claude CLI when it is installed, and
    only fail when neither can answer. Returns (backend_used, reply_text).
    """
    be = backend(kind)
    try:
        return be, be.complete(prompt)
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        if isinstance(be, LocalBackend) and shutil.which("claude"):
            print(f"local backend gave nothing usable ({exc}) — falling back to claude", file=sys.stderr)
            fb = ClaudeBackend()
            return fb, fb.complete(prompt)
        raise RuntimeError(
            f"no backend answered: local server at {getattr(be, 'url', '?')} "
            f"unreachable ({exc}) and no claude CLI on PATH — start one with "
            f"`mlx_lm.server --model {DEFAULT_MODEL}`"
        ) from exc


def ask_and_parse(prompt: str, parser, kind: str | None = None):
    """One completion plus one repair round when the reply doesn't parse.

    A local model at temperature 0 is deterministic: retrying the same prompt
    reproduces the same malformed JSON byte for byte. What changes the outcome
    is showing the model its own reply and the parse error — a short prompt,
    so the repair round costs seconds where the original cost minutes.
    Returns (backend_used, parsed).
    """
    be, reply = plan_with_fallback(prompt, kind)
    try:
        return be, parser(reply)
    except ValueError as exc:
        repair = (
            f"Your previous reply could not be parsed: {exc}\n"
            "Reply again with ONLY the corrected JSON — same content, valid syntax, "
            "no prose around it.\n\nPrevious reply:\n" + reply
        )
        return be, parser(be.complete(repair))


# -------------------------------------------------------------------- plan io --
def plan_path(root: Path) -> Path:
    return root / "data" / "commit_plan.json"


def save_plan(root: Path, plan: list[PlannedCommit], model_name: str) -> None:
    plan_path(root).parent.mkdir(parents=True, exist_ok=True)
    plan_path(root).write_text(
        json.dumps(
            {
                "fingerprint": tree_fingerprint(root),
                "model": model_name,
                "commits": [{"message": p.message, "files": p.files} for p in plan],
            },
            indent=2,
        )
    )


def load_plan(root: Path) -> tuple[list[PlannedCommit], str] | None:
    """The saved plan, but only while the tree it described still exists."""
    try:
        doc = json.loads(plan_path(root).read_text())
    except (OSError, json.JSONDecodeError):
        return None
    if doc.get("fingerprint") != tree_fingerprint(root):
        return None
    plan = [PlannedCommit(message=c["message"], files=list(c["files"])) for c in doc.get("commits", [])]
    return (plan, str(doc.get("model", "unknown"))) if plan else None


# -------------------------------------------------------------------- apply --
def apply_plan(root: Path, plan: list[PlannedCommit], model_name: str) -> list[str]:
    """Stage and commit each group, as ordinary commits.

    Ordinary on purpose: the pre-commit hook still runs, so a breaking change
    is still blocked by the impact gate regardless of who wrote the message.
    Each commit is a provenance action — intent before staging, execution
    carrying the sha — and the message ends with the model's name, so `git log`
    answers "who split this" without consulting the ledger.
    """
    from pf.provenance import action

    # An extra trailer, verbatim, when the caller owes one — e.g. a session
    # driven by a hosted model attributing itself alongside the local splitter.
    extra = os.environ.get("PF_COMMIT_TRAILER", "").strip()

    shas: list[str] = []
    for commit in plan:
        message = f"{commit.message.rstrip()}\n\nCommit-Split-By: {model_name}\n"
        if extra:
            message += f"{extra}\n"
        with action(
            root, tool="pf.committer", target=commit.subject, summary=f"commit split by {model_name}: {commit.subject}"
        ) as a:
            _git(root, "add", "-A", "--", *commit.files)
            _git(root, "commit", "-m", message)
            sha = _git(root, "rev-parse", "--short", "HEAD").strip()
            a["detail"] = f"{sha} ({len(commit.files)} files)"
            shas.append(sha)
    plan_path(root).unlink(missing_ok=True)
    return shas
