"""Claude Code workflow runs, written inside the repo instead of under ~/.claude.

The harness writes a workflow run's journal and every subagent transcript to
`<home>/projects/<slug>/<session>/subagents/workflows/<run-id>/`, and the script
that defined the run to `<home>/projects/<slug>/<session>/workflows/scripts/`.
Both paths are keyed by session id: a `/clear`, a new terminal or a resumed
session hides them, and nothing in the repo points at them. The evidence a run
produced then survives only as long as someone remembers a uuid.

The fix is to make those two directories symlinks into the repo, so the harness
writes a run to `<root>/logs/workflows/<run-id>/` in the first place. `link()`
creates them and a SessionStart hook calls it for every session, before any run
can start. Nothing is copied and nothing is moved after the fact: the file the
agent is appending to *is* the file in the repo, which is what makes progress
visible while the run is still going. `logs/` is ignored by git, so the runs cost
nothing on a branch. Which directories may be linked is not a free choice;
`_pairs` has the constraint, which is Claude Code's own retention sweep.

What a linked run loses is its session: every linked session reaches the same
directory, so finding a run through one is no evidence that it launched it, and
`discover()` says nothing rather than guessing. Run ids are unique, and the
launch record left in the session folder still names the owner by hand.

Copying survives for one job, adoption: runs that a session wrote before it was
linked, on this machine or another. `mirror()` copies such a run into the repo
and `finalize()` removes the session copy, but only after SHA-256 verification,
because the harness appends to a transcript while the agent runs and a copy taken
mid-write can be short by a few kilobytes and still look complete by name and
size. A run written through a link is never a candidate: `discover()` gives it no
`source`, and `_aliased()` refuses any path that would make a copy verify
against itself.

"Complete" is a heuristic because the journal has no end-of-run marker. Every
started agent having a result or failed record is necessary but not sufficient:
between two phases a live run looks exactly like a finished one for a few
seconds. So a run also has to be quiet (nothing changed for `quiet_for` seconds)
before it counts as complete, and only complete runs are ever finalized.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import re
import shutil
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

RUNS_DIR = "logs/workflows"
SCRIPTS_DIR = "logs/workflows/scripts"
#: Where a session's own working directories are pointed. `.tmp/` rather than
#: `logs/`: this is scratch, not a durable run record, and `.tmp/` is ignored.
#: Namespaced by session id so two sessions in one checkout cannot overwrite
#: each other, which is also what makes the directory readable afterwards.
SCRATCH_DIR = ".tmp"

#: Session directories the harness keeps under a temp root instead of the
#: Claude Code folder: scratch files, background task output, pasted images.
#: Nothing sweeps these (the retention walk in _pairs() reaches only the Claude
#: Code folder), so each is linked whole rather than by leaf.
SCRATCH_KINDS = ("scratchpad", "tasks", "images")


def _tmp_roots() -> list[Path]:
    """Every base the harness might put a session's working directories under.

    Discovered rather than hardcoded. `/private/tmp/claude-<uid>/` is today's
    shape on macOS; it is a convention, not an interface, and a link that
    silently stops being made after a harness change is exactly the failure
    this function exists to avoid.
    """
    seen: list[Path] = []
    for v in (os.environ.get("TMPDIR"), tempfile.gettempdir(), "/tmp", "/private/tmp"):
        if not v:
            continue
        with contextlib.suppress(OSError):
            r = Path(v).resolve()
            if r.is_dir() and r not in seen:
                seen.append(r)
    return seen


def scratch_session(slug_: str, session_id: str, *, create: bool = False) -> Path | None:
    """The harness's temp directory for one session, or None if it has none.

    The conventional `claude-<uid>` segment is tried first and a one-level scan
    follows, so renaming that segment changes which directory is found rather
    than stopping the search. Both legs require `<slug>/<session-id>` beneath,
    which is specific enough that a stranger's directory cannot match.
    """
    if not slug_ or not session_id:
        return None
    uid = getattr(os, "getuid", lambda: None)()
    for base in _tmp_roots():
        if uid is not None:
            direct = base / f"claude-{uid}" / slug_ / session_id
            if direct.is_dir():
                return direct
        with contextlib.suppress(OSError):
            for child in sorted(base.iterdir()):
                cand = child / slug_ / session_id
                if cand.is_dir():
                    return cand
    if not create or uid is None:
        return None
    # Nothing found and one is wanted: at SessionStart the harness has often
    # not made the folder yet, and a link made after the first write is already
    # too late for it. Only the conventional shape can be built blind, so that
    # is what is built -- discovery above is what keeps a rename working.
    # Which root, when several exist, is decided by where this repo already
    # has sessions, not by the order _tmp_roots() returns. TMPDIR on macOS is
    # a per-user folder under /var/folders while the harness uses /private/tmp;
    # creating it in the wrong one makes a link the harness never looks at.
    seg = f"claude-{uid}"
    bases = _tmp_roots()

    def population(b: Path) -> int:
        """How many of this repo's sessions already live under this root."""
        try:
            return sum(1 for _ in (b / seg / slug_).iterdir())
        except OSError:
            return -1

    ranked = sorted(bases, key=lambda b: (-population(b), bases.index(b)))
    for base in ranked:
        made = base / seg / slug_ / session_id
        with contextlib.suppress(OSError):
            made.mkdir(parents=True, exist_ok=True)
            return made
    return None

QUIET_FOR = 120.0
# Files adoption adds beside the harness's own. They are excluded from
# last_change so a freshly written README does not make an adopted run look live.
ADOPTION_EXTRAS = frozenset({"README.md", "script.js"})
# Width of the running-agent label at the end of a progress line.
LABEL_WIDTH = 23
# A live transcript grows by a few kilobytes every round. Printing a progress
# line for each growth turned the watcher into a two-second ticker; size now
# counts as a change only when it crosses a step of this many bytes.
SIZE_STEP = 256_000
_META_NAME = re.compile(r"\bname\s*:\s*['\"]([^'\"]+)['\"]")


def slug(root: Path) -> str:
    """Claude Code's folder name for a repo: the absolute path with every
    character outside [A-Za-z0-9] replaced by "-". Underscores included, which
    is why `data_platform` and `data-platform` collapse to the same text."""
    return re.sub(r"[^A-Za-z0-9]", "-", str(Path(root).absolute()))


def claude_home() -> Path:
    """`expanduser` because CLAUDE_CONFIG_DIR is often written with a `~`, and
    a `~` the shell never expanded would silently name a directory in the cwd,
    where there are no sessions and every link would be built in the wrong
    place."""
    configured = os.environ.get("CLAUDE_CONFIG_DIR")
    return Path(configured).expanduser() if configured else Path.home() / ".claude"


def slugs(root: Path) -> list[str]:
    """Every folder name Claude Code could file this repo's sessions under. The
    slug comes from the cwd, and `pf work <group> <project>` launches with the
    project as cwd, so a session started that way lands in its own folder. Its
    runs belong to this repo just as much as a session started at the root, so
    the project directories are listed too. Prefix matching would be simpler and
    wrong: a sibling checkout called `<repo>-extra` has a slug that starts with
    this repo's."""
    out = [slug(root)]
    for p in sorted((root / "groups").glob("*/projects/*")):
        if p.is_dir():
            out.append(slug(p))
    return out


def sessions(root: Path, home: Path) -> list[Path]:
    """Session directories of this repo only, root and projects alike. `memory`
    sits beside them and is not a session; the per-session `.jsonl` transcripts
    are files, not dirs."""
    out: list[Path] = []
    for name in slugs(root):
        projects = home / "projects" / name
        if projects.is_dir():
            # `is_symlink` first: is_dir() follows a link, so a session entry
            # pointing at an unrelated directory would otherwise be treated as
            # one of this repo's and have its contents adopted.
            out += [p for p in projects.iterdir()
                    if p.is_dir() and not p.is_symlink() and p.name != "memory"]
    return sorted(out, key=lambda p: (p.parent.name, p.name))


def human_size(n: int | float) -> str:
    if n < 1000:
        return f"{int(n)} B"
    if n < 1e6:
        return f"{n / 1e3:.1f} kB"
    if n < 1e9:
        return f"{n / 1e6:.1f} MB"
    return f"{n / 1e9:.1f} GB"


@dataclass(frozen=True)
class Agent:
    agent_id: str
    label: str
    phase: str
    state: str  # running | done | failed


@dataclass
class Run:
    run_id: str
    name: str = ""
    session: str = ""  # the session that launched it; "" when that is unknown
    # A session copy that is not in the repo, and so is a candidate for
    # adoption. A run written through a link has none: it was written into the
    # repo directly, and the session path is only another name for `mirror`.
    source: Path | None = None
    mirror: Path | None = None
    script: Path | None = None
    agents: list[Agent] = field(default_factory=list)
    files: int = 0
    bytes: int = 0
    last_change: float = 0.0  # epoch of the newest harness-written file
    quiet_for: float = QUIET_FOR

    @property
    def in_repo(self) -> bool:
        """The repo holds this run and nothing outside it does. False while a
        session copy is still waiting to be adopted, even once it is copied."""
        return self.mirror is not None and self.source is None

    @property
    def started(self) -> int:
        return len(self.agents)

    @property
    def finished(self) -> int:
        return sum(a.state != "running" for a in self.agents)

    @property
    def failed(self) -> int:
        return sum(a.state == "failed" for a in self.agents)

    @property
    def live(self) -> bool:
        """Still running, or changed too recently to be sure it is not."""
        return (self.started > self.finished
                or time.time() - self.last_change < self.quiet_for)

    @property
    def complete(self) -> bool:
        return not self.live

    @property
    def phases(self) -> dict[str, tuple[int, int]]:
        """phase -> (started, finished), in the order the phases began."""
        out: dict[str, tuple[int, int]] = {}
        for a in self.agents:
            s, f = out.get(a.phase, (0, 0))
            out[a.phase] = (s + 1, f + (a.state != "running"))
        return out

    def progress_line(self) -> str:
        """One line for a watcher: the phase the run is in with that phase's
        counts, the run-wide failure count, the size, and the label of the
        agent that started most recently and is still running."""
        parts = [" ".join(p for p in (self.run_id, self.name) if p)]
        if self.agents:
            phase = self.agents[-1].phase
            s, f = self.phases[phase]
            mid = f"{phase or 'agents'} {f}/{s} done"
            if self.failed:
                mid += f" ({self.failed} failed)"
            parts.append(mid)
        else:
            parts.append("launched, no agents yet")
        parts.append(human_size(self.bytes))
        running = [a for a in self.agents if a.state == "running"]
        if running:
            label = running[-1].label
            if len(label) > LABEL_WIDTH:
                label = label[:LABEL_WIDTH - 1] + "…"
            parts.append(label)
        return " · ".join(parts)


@dataclass
class MirrorReport:
    run_id: str
    copied: list[str]
    bytes: int
    skipped: int
    refused: str = ""  # why nothing was written; "" when the mirror was written


@dataclass
class SyncResult:
    run_id: str
    name: str
    copied: int
    bytes: int
    moved: bool
    note: str
    refused: str = ""  # mirror() wrote nothing, so finalize was not tried


# --- reading a run -----------------------------------------------------------


def _agents(d: Path) -> list[Agent]:
    """Journal order, journal state, meta label and phase when the meta file
    exists. The journal's last line may be half-written while the run is live,
    so an unparsable line is skipped rather than fatal."""
    meta: dict[str, dict] = {}
    for m in sorted(d.glob("agent-*.meta.json")):
        aid = m.name[len("agent-"):-len(".meta.json")]
        try:
            meta[aid] = json.loads(m.read_text())
        except (OSError, ValueError):
            meta[aid] = {}
    order: list[str] = []
    rows: dict[str, dict[str, str]] = {}
    journal = d / "journal.jsonl"
    if journal.is_file():
        for line in journal.read_text(errors="replace").splitlines():
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            aid = rec.get("agentId") if isinstance(rec, dict) else None
            if not aid:
                continue
            row = rows.get(aid)
            if row is None:
                order.append(aid)
                row = rows[aid] = {"label": rec.get("label", ""),
                                   "phase": rec.get("phase", ""), "state": "running"}
            if rec.get("type") == "result":
                row["state"] = "done"
            elif rec.get("type") == "failed":
                row["state"] = "failed"
    for aid in meta:
        if aid not in rows:
            order.append(aid)
            rows[aid] = {"label": "", "phase": "", "state": "running"}
    out = []
    for aid in order:
        row, m = rows[aid], meta.get(aid, {})
        out.append(Agent(aid, m.get("description") or row["label"],
                         m.get("workflowPhase") or row["phase"], row["state"]))
    return out


def _load(d: Path, quiet_for: float) -> Run:
    """A run as it is on disk right now. Files can vanish between the listing
    and the stat: `git clean -xdf` takes `logs/` with it, adoption moves a run
    while a `watch` in another terminal is scanning it, and Claude Code's own
    retention sweep removes a link under a reader. A scan that dies on any of
    those leaves the watcher dead exactly when it was showing something, so a
    file that cannot be stat'd is skipped."""
    stats = []
    for p in d.rglob("*"):
        try:
            if p.is_file():
                stats.append((p, p.stat()))
        except OSError:  # vanished, or unreadable through a broken link
            continue
    harness = [st.st_mtime for p, st in stats if p.name not in ADOPTION_EXTRAS]
    try:
        fallback = d.stat().st_mtime
    except FileNotFoundError:
        fallback = 0.0
    return Run(run_id=d.name, agents=_agents(d), files=len(stats),
               bytes=sum(st.st_size for _, st in stats),
               last_change=max(harness) if harness else fallback,
               quiet_for=quiet_for)


def _is_run(d: Path) -> bool:
    """Anything the harness has begun writing a run into. The journal usually
    settles it, but a run is a directory for a moment before it is journalled,
    and treating that moment as "not a run" both hides it from `list` and makes
    adoption refuse the whole session for holding something it cannot name.
    `scripts/`, the only other directory here, matches none of these."""
    return ((d / "journal.jsonl").is_file()
            or any(d.glob("agent-*.jsonl")) or any(d.glob("agent-*.meta.json")))


def _script_in(scripts: Path, run_id: str) -> Path | None:
    """The `<name>-<run-id>.js` the harness wrote for this run, if it is here."""
    if not scripts.is_dir():
        return None
    for p in sorted(scripts.glob("*.js")):
        if p.stem.endswith("-" + run_id):
            return p
    return None


def _script_for(session: Path, run_id: str) -> Path | None:
    return _script_in(session / "workflows" / "scripts", run_id)


def _name_in(script: Path | None) -> str:
    """An adopted run keeps the script as `script.js`, losing the name the
    filename carried, so it has to come from the `meta.name` inside."""
    if script is None or not script.is_file():
        return ""
    try:
        head = script.read_text(errors="replace")[:4000]
    except OSError:
        return ""
    m = _META_NAME.search(head)
    return m.group(1) if m else ""


def discover(root: Path, home: Path, *, quiet_for: float = QUIET_FOR) -> list[Run]:
    """Every run of this repo: written into it, still in a session folder, or
    both. Keyed by run id, so one run seen twice is one Run.

    A linked session's `subagents/workflows` *is* the repo's runs directory, so
    walking it would read every run a second time, once per linked session, and
    attribute runs to whichever session happened to be walked last. Those
    sessions are skipped and the repo walk covers them, which is also why a run
    written in place carries no session: every linked session reaches it, so
    naming one would be a guess. Other repos' slugs are never opened."""
    runs: dict[str, Run] = {}
    repo_runs = (root / RUNS_DIR).resolve()
    # A link can point either way. Only one of them puts the bytes in the repo:
    # if logs/workflows is itself a link out to a session folder, a run reached
    # through it is still stored under ~/.claude, and calling it ours would
    # report the opposite of the truth.
    holds_runs = repo_runs.is_relative_to(root.resolve())
    for sess in sessions(root, home):
        wf = sess / "subagents" / "workflows"
        try:
            if holds_runs and wf.resolve() == repo_runs:
                continue  # linked; the repo walk below reaches exactly these
            dirs = sorted(p for p in wf.iterdir() if p.is_dir() and _is_run(p))
        except (OSError, RuntimeError):
            # No directory, or one that cannot be walked: a link pointing at a
            # file raises NotADirectoryError and one that loops raises ELOOP,
            # which pathlib re-raises as RuntimeError. None of them is a reason
            # for `list` to stop listing the other sessions.
            continue
        for d in dirs:
            run = _load(d, quiet_for)
            run.session = sess.name
            run.source = d
            run.script = _script_for(sess, d.name)
            run.name = run.script.stem[:-len(d.name) - 1] if run.script else ""
            prev = runs.get(d.name)
            # Two sessions can hold the same run id only when one is a copy.
            # Prefer a sighting that still has a session copy over one that does
            # not, and among two copies the one that changed most recently: that
            # is the one still being written, and reporting the other would say
            # the run is in hand while its bytes grow under ~/.claude. Adoption
            # takes the newest each pass, so the older ones are reached in turn.
            if (prev is None or prev.source is None
                    or run.last_change > prev.last_change):
                runs[d.name] = run
    repo = root / RUNS_DIR
    if repo.is_dir():
        for d in sorted(p for p in repo.iterdir() if p.is_dir() and _is_run(p)):
            run = runs.get(d.name)
            if run is None:
                run = runs[d.name] = _load(d, quiet_for)
                run.script = _script_in(root / SCRIPTS_DIR, d.name)
                run.name = run.script.stem[:-len(d.name) - 1] if run.script else ""
            elif run.source is not None and _aliased(run.source, d):
                continue
            run.mirror = d
            if not run.name:
                run.name = _name_in(d / "script.js")
    return sorted(runs.values(), key=lambda r: r.last_change, reverse=True)


# --- linking a session into the repo -----------------------------------------


@dataclass
class LinkReport:
    session: str
    kind: str  # runs | scripts
    path: Path  # the session directory that should point into the repo
    target: Path  # the repo directory it should point at
    state: str  # linked | created | adopted | unlinked | refused
    note: str = ""

    @property
    def ok(self) -> bool:
        return self.state in ("linked", "created", "adopted", "narrowed")

    def line(self, root: Path) -> str:
        where = self.target.relative_to(root) if self.target.is_relative_to(root) else self.target
        head = f"{self.session[:8] or '?'} {self.kind:<7} {self.state}"
        if self.state in ("created", "adopted", "linked"):
            head += f" -> {where}"
        return f"{head}{': ' + self.note if self.note else ''}"


def _pairs(session: Path, root: Path) -> list[tuple[str, Path, Path, Path]]:
    """The session directories to replace with links, each with the repo
    directory it should point at.

    A run is split across three places: `subagents/workflows/<run-id>/` holds the
    journal and the transcripts, `workflows/scripts/<name>-<run-id>.js` the
    script, and `workflows/<run-id>.json` a launch record. The first two are
    linked; `workflows/` itself is not, and the launch record is left behind.

    The reason is Claude Code's retention sweep. For a session whose transcript
    it has already removed, it walks three directories:

        for (const c of ["subagents", "workflows", "remote-agents"])
            if (await isDir(join(dir, c))) await purge(join(dir, c), cutoff)

    and `purge` recurses with `readdir`, deletes every file older than
    `cleanupPeriodDays` (30 by default) and prunes the directories it empties.
    `readdir` follows a symlinked directory, so following one of those three
    paths into the repo would delete run history a month later.

    Today it would not get that far: `isDir` is `lstat(p).isDirectory()`, which
    is false for a symlink, so a link at `workflows/` is skipped rather than
    entered (checked in 2.1.250, 2.1.261 and 2.1.263). That is a safe accident,
    not a guarantee: it turns on `lstat` rather than `stat`, one character in a
    minified bundle, and nothing tells us when it changes.

    Linking a leaf entry needs no such luck. `purge` reaches an entry that is
    neither a directory nor a file through its final branch, which lstats it and
    at most unlinks the link, leaving what it points at alone. So
    `subagents/workflows` and `workflows/scripts` are safe under both readings,
    and the next session's hook puts back any link the sweep removes. The launch
    record only duplicates the script text, which is in `scripts/`, so what stays
    behind is a timestamp and a task id."""
    pairs = [("runs", session / "subagents" / "workflows", root / RUNS_DIR, session),
             ("scripts", session / "workflows" / "scripts", root / SCRIPTS_DIR, session)]
    tmp = scratch_session(slug(root), session.name, create=True)
    if tmp is not None:
        here = root / SCRATCH_DIR / session.name
        pairs += [(k, tmp / k, here / k, tmp) for k in SCRATCH_KINDS]
    return pairs


def _narrow(session: Path, root: Path, *, dry_run: bool) -> str:
    """Undo a link at `workflows/` itself, and say what was done, or "" when
    there is nothing to undo. An earlier version of this command linked that
    whole directory, which is one of the three the retention sweep walks: safe
    only while that sweep happens to test it with `lstat` (see `_pairs`), and not
    worth depending on. What the link pointed at stays in the repo; only the link
    is replaced by the plain directory the harness expects to find."""
    wide = session / "workflows"
    if not wide.is_symlink():
        return ""
    try:
        if not wide.resolve().is_relative_to((root / RUNS_DIR).resolve()):
            return ""  # someone else's link, and not this command's to remove
    except (OSError, RuntimeError):
        return ""
    if dry_run:
        return "links into the repo from a directory the retention sweep walks"
    wide.unlink()
    wide.mkdir(parents=True, exist_ok=True)
    return "no longer links into the repo; only scripts/ does"


def _adopt(kind: str, path: Path, target: Path, root: Path, session: Path,
           quiet_for: float, log: Callable[[str], None] | None) -> str:
    """Move what a session wrote before it was linked into the repo, and return
    "" when the directory is empty afterwards or the reason it is not.

    Nothing is deleted that was not first copied and verified by hash, and a
    live run is a refusal rather than a wait: the link can be made on the next
    session, and taking a directory out from under a running harness cannot.
    Anything unrecognised is also a refusal, because the alternative is deciding
    on someone's behalf that a file in their session folder is disposable.

    Liveness is checked for every run before any of them is touched. Finding out
    half way through leaves some runs moved, one copied but not moved, and the
    link still not made, which is three states to explain instead of one."""
    live = [e.name for e in sorted(path.iterdir())
            if kind == "runs" and e.is_dir() and not e.is_symlink() and _is_run(e)
            and _load(e, quiet_for).live]
    if live:
        return (f"{live[0]} is still running" if len(live) == 1
                else f"{len(live)} runs are still running ({live[0]} and others)")
    for entry in sorted(path.iterdir()):
        # A link into the repo left by an earlier version of this command:
        # what it pointed at is already here, so only the link is left to drop.
        if entry.is_symlink():
            if entry.resolve().is_relative_to(target.resolve()):
                entry.unlink()
                continue
            # Points somewhere else entirely. Copying what it points at and then
            # removing it is not this command's call, and rmtree refuses a link
            # anyway, which would leave the session unlinkable with an OSError
            # for an explanation.
            return f"{entry.name} is a link to {entry.readlink()}; move it by hand"
        if entry.is_dir():
            if kind == "runs" and _is_run(entry):
                run = _load(entry, quiet_for)
                run.session, run.source = session.name, entry
                run.script = _script_for(session, entry.name)
                rep = mirror(run, root, log=log)
                if rep.refused:
                    return f"{entry.name}: {rep.refused}"
                moved, note = finalize(run, root, log=log)
                if not moved:
                    return f"{entry.name}: {note}"
                continue
            return f"{entry.name} is not something this command knows how to move"
        if kind == "runs":
            return f"{entry.name} is not a workflow run; move it by hand"
        note = _adopt_one(entry, target / entry.name, log)
        if note:
            return note
    return ""


def _adopt_one(entry: Path, dst: Path, log: Callable[[str], None] | None) -> str:
    """Copy one file into the repo, prove it by hash, then remove the original.
    A destination that already holds different bytes is left alone: two runs
    never share a name, so that means something unexpected, not a retry."""
    if entry.resolve() == dst.resolve():
        # Reached through a link, so the copy would be the file copying onto
        # itself and the unlink below would delete it. Nothing to adopt.
        return ""
    if dst.is_file():
        if _sha256(dst) != _sha256(entry):
            return f"{entry.name} is already in the repo with different content"
    else:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(entry, dst)
        if _sha256(dst) != _sha256(entry):
            return f"{entry.name} did not copy cleanly"
    entry.unlink()
    if log is not None:
        log(f"adopted {entry.name}")
    return ""


def _link_one(kind: str, path: Path, target: Path, root: Path, home: Path, session: Path,
              *, adopt: bool, dry_run: bool, quiet_for: float,
              log: Callable[[str], None] | None) -> LinkReport:
    def rep(state: str, note: str = "") -> LinkReport:
        return LinkReport(session.name, kind, path, target, state, note)

    home_real = home.resolve()
    if target.resolve() == home_real or home_real in target.resolve().parents:
        return rep("refused", "the target is inside the Claude Code folder")
    if not dry_run:
        # Before anything else, because `logs/` is ignored by git: one
        # `git clean -xdf` leaves every link dangling, and a dangling link is
        # worse than no link at all. The harness cannot create a run directory
        # through one, so the run fails rather than landing somewhere else.
        target.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        if path.resolve() != target.resolve():
            return rep("refused", f"already a link to {path.readlink()}")
        if not target.is_dir():
            return rep("unlinked", "the directory it points at is missing")
        return rep("linked")
    # Checked before anything else about `path`, and not gated on it existing: a
    # symlinked `subagents/` pointing at a directory with no `workflows` child
    # passes every other test here and ends at symlink_to(), which writes a link
    # into a stranger's directory and then reports the session as linked.
    if not path.parent.resolve().is_relative_to(session.resolve()):
        return rep("refused", f"{path.parent} leads outside the session folder")
    if path.exists() and not path.is_dir():
        return rep("refused", "exists and is not a directory")
    if path.is_dir() and path.resolve() == target.resolve():
        # Not a link itself, but reached through one higher up, so its contents
        # are already the target's. _narrow() removes that parent link before
        # this runs; reporting it is for --check, which changes nothing. Adopting
        # would copy every file onto itself and then delete it.
        return rep("unlinked", "reached through a link at workflows/")
    entries = sorted(path.iterdir()) if path.is_dir() else []
    # Before any refusal: a report asked for with --check states what is there,
    # and must not depend on which flags the caller happened to pass.
    if dry_run:
        return rep("unlinked", f"{len(entries)} item(s) to adopt" if entries else "")
    if entries and not adopt:
        return rep("refused", f"holds {len(entries)} item(s) written before it was "
                              "linked; re-run with --adopt")
    if entries:
        note = _adopt(kind, path, target, root, session, quiet_for, log)
        if note:
            return rep("refused", note)
    if path.is_dir():
        try:
            path.rmdir()
        except OSError as exc:  # something landed in it while we were adopting
            return rep("refused", f"cannot replace the directory: {exc}")
    path.parent.mkdir(parents=True, exist_ok=True)
    # Absolute, never relative: the link is read from the session folder, which
    # is nowhere near the repo, and `root` is only absolute by convention.
    path.symlink_to(target.absolute())
    return rep("adopted" if entries else "created")


def link(root: Path, home: Path, *, session_dir: Path | None = None, adopt: bool = False,
         dry_run: bool = False, quiet_for: float = QUIET_FOR,
         log: Callable[[str], None] | None = None) -> list[LinkReport]:
    """Point a session's run and script directories at the repo, so the harness
    writes future runs inside it. Idempotent: an existing correct link reports
    `linked` and is left alone.

    `session_dir` names one session and is created if it does not exist yet,
    which is what the SessionStart hook needs: at that moment the harness has
    not necessarily made the folder, and a link created afterwards would miss
    the first run of the session. Without it, every session of this repo is
    linked, which is how an old session gets adopted by hand."""
    out: list[LinkReport] = []
    for sess in ([session_dir] if session_dir is not None else sessions(root, home)):
        here: list[LinkReport] = []
        note = _narrow(sess, root, dry_run=dry_run)
        if note:
            here.append(LinkReport(sess.name, "sweep", sess / "workflows", root / RUNS_DIR,
                                   "unlinked" if dry_run else "narrowed", note))
        for kind, path, target, owner in _pairs(sess, root):
            try:
                here.append(_link_one(kind, path, target, root, home, owner, adopt=adopt,
                                      dry_run=dry_run, quiet_for=quiet_for, log=log))
            except (OSError, RuntimeError) as exc:
                # A target that became a file, or a loop: pathlib raises
                # RuntimeError rather than OSError for a symlink cycle, and a
                # link command must report that, not traceback out of the CLI.
                here.append(LinkReport(sess.name, kind, path, target, "refused",
                                       f"{type(exc).__name__}: {exc}"))
        for r in here:
            if log is not None and r.state != "linked":
                log(r.line(root))
        out.extend(here)
    # Refreshed whenever a link is in place, not only when one was just made:
    # otherwise the explanation in the directory keeps whatever wording it had
    # on the day it was created.
    if not dry_run and any(r.ok for r in out):
        _write_dir_readme(root)
    return out


def _write_dir_readme(root: Path) -> None:
    path = root / RUNS_DIR / "README.md"
    text = "\n".join([
        "# Workflow runs",
        "",
        "Claude Code writes each `Workflow` run here as it happens. The session",
        "directories it would otherwise use,",
        "`~/.claude/projects/<slug>/<session>/subagents/workflows` and",
        "`.../workflows/scripts`, are symlinks to this folder and to `scripts/`,",
        "created by `pf workflow link` from a SessionStart hook.",
        "",
        "- `<run-id>/journal.jsonl`: launched, started, result and failed records",
        "- `<run-id>/agent-<id>.jsonl`: one subagent's transcript, `.meta.json` its label",
        "- `scripts/<name>-<run-id>.js`: the script that defined the run; pass it back",
        "  to the Workflow tool with `resumeFromRunId` to resume",
        "",
        "`<run-id>.json`, the launch record, stays under `~/.claude`: linking the",
        "directory it sits in would let Claude Code's retention sweep follow the link",
        "and delete this history. A few are here from before that was understood.",
        "",
        "`pf workflow list` indexes them, `pf workflow watch` follows a live one and",
        "`pf workflow show <run-id>` prints one run's phases and agents.",
        "",
        "Ignored by git via `**/logs/`: these are evidence for the branch you are on,",
        "not something to commit.",
        "",
    ])
    if not path.is_file() or path.read_text() != text:
        path.write_text(text)


# --- adopting a run that was written outside the repo ------------------------


def _plan(run: Run) -> list[tuple[Path, Path, str]]:
    """(source, destination, name) for every file the mirror must hold. The
    script lives outside the run dir, so it is copied in as `script.js`."""
    if run.source is None or run.mirror is None:
        return []
    plan = [(p, run.mirror / p.relative_to(run.source), str(p.relative_to(run.source)))
            for p in sorted(run.source.rglob("*")) if p.is_file()]
    if run.script is not None and run.script.is_file():
        plan.append((run.script, run.mirror / "script.js", "script.js"))
    return plan


def _stale(src: Path, dst: Path) -> bool:
    """copy2 preserves mtime, so an unchanged file matches by size and mtime
    and is skipped. A live transcript that grew fails on size; one rewritten
    at the same size fails on mtime. Hash checks are left to verify()."""
    if not dst.is_file():
        return True
    try:
        a, b = src.stat(), dst.stat()
    except FileNotFoundError:
        return False  # the source went away; there is nothing left to copy
    return a.st_size != b.st_size or abs(a.st_mtime - b.st_mtime) > 0.001


def _aliased(source: Path, mirror: Path) -> str:
    """Why `mirror` would alias `source` instead of holding a copy of it, or ""
    when it would not. `ln -s` into logs/workflows/ is the obvious hand-made way
    to see a run in the repo, and it is the one thing copy-then-verify cannot
    survive: every file hashes against itself, verify() passes, and finalize()
    removes the only copy. The resolved paths are compared, not just the entry,
    because a link at logs/workflows itself makes every entry a real directory
    that still lives in the session folder."""
    if mirror.is_symlink():
        return "mirror path is a symlink"
    src, dst = source.resolve(), mirror.resolve()
    if dst == src or src in dst.parents or dst in src.parents:
        return "mirror path resolves into the session folder"
    return ""


def _readme(run: Run) -> str:
    return "\n".join([
        f"# Workflow run {run.run_id}",
        "",
        f"- name: {run.name or '(unnamed)'}",
        f"- session: {run.session or '(unknown)'}",
        f"- origin: {run.source}",
        (f"- agents: {run.started} started, {run.finished} finished, "
         f"{run.failed} failed"),
        "",
        "- `script.js`: the workflow script that defined the run",
        "- `journal.jsonl`: launched, started, result and failed records, in order",
        ("- `agent-<id>.jsonl`: one subagent's transcript; "
         "`agent-<id>.meta.json` its label and phase"),
        "",
        ("Written by a session that was not linked into the repo, then adopted by "
         "`pf workflow link --adopt` or `pf workflow sync --move`. A run written "
         "through a link has no README: nothing writes into it. Ignored by git "
         "via `**/logs/`."),
        "",
    ])


def mirror(run: Run, root: Path, *, log: Callable[[str], None] | None = None) -> MirrorReport:
    """Copy what is missing or stale into <root>/logs/workflows/<run-id>/.

    A run without a source has nothing to copy and gets an empty report. So
    does a mirror path that would alias the source; `refused` says why, and
    nothing is written through it, not even the README. The README is
    generated, not copied, so it is never listed under `copied`."""
    if run.source is None:
        return MirrorReport(run.run_id, [], 0, 0)
    run.mirror = root / RUNS_DIR / run.run_id
    refused = _aliased(run.source, run.mirror)
    if refused:
        return MirrorReport(run.run_id, [], 0, 0, refused)
    run.mirror.mkdir(parents=True, exist_ok=True)
    plan = _plan(run)
    todo = [(s, d, n) for s, d, n in plan if _stale(s, d)]
    copied: list[str] = []
    total = 0
    for i, (src, dst, name) in enumerate(todo, 1):
        dst.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copy2(src, dst)
        except FileNotFoundError:
            break  # the run was moved under us; the next round sees the mirror
        size = dst.stat().st_size
        copied.append(name)
        total += size
        if log is not None:
            log(f"[{i}/{len(todo)}] {100 * i // len(todo):3d}% {name} {size / 1e3:.1f} kB")
    readme = run.mirror / "README.md"
    text = _readme(run)
    if not readme.is_file() or readme.read_text() != text:
        readme.write_text(text)
    return MirrorReport(run.run_id, copied, total, len(plan) - len(todo))


def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verify(run: Run) -> list[str]:
    """Names whose mirror copy is missing or differs from the source by hash.
    Nothing to check without a source; everything is missing without a mirror."""
    if run.source is None:
        return []
    if run.mirror is None:
        return [str(p.relative_to(run.source)) for p in sorted(run.source.rglob("*"))
                if p.is_file()] + (["script.js"] if run.script else [])
    out = []
    for src, dst, name in _plan(run):
        try:
            if not dst.is_file() or _sha256(src) != _sha256(dst):
                out.append(name)
        except FileNotFoundError:
            out.append(name)  # a source that vanished mid-check is not verified
    return out


def finalize(run: Run, root: Path, *, log: Callable[[str], None] | None = None) -> tuple[bool, str]:
    """Remove the session copy, and only that. Refused while any agent runs,
    while the run is inside its quiet period, while any mirrored file fails
    verification, and when the mirror path aliases the source, because then
    verification compared every file with itself. The script file in the
    session is never removed: it is the one thing that still names the run if
    a mirror is ever lost."""
    if run.source is None:
        return False, "no session copy to remove"
    # Judged from disk now, not from the snapshot discover() took: a run that
    # resumed since then has a new agent in its journal, and the snapshot
    # would still say every agent finished long ago.
    now = _load(run.source, run.quiet_for)
    if now.started > now.finished:
        return False, (f"live: {now.started - now.finished} of {now.started} "
                       "agents still running")
    # Floored at QUIET_FOR whatever the caller asked for. `--quiet-for` exists to
    # relabel a run live or complete in `list` and `watch`, which is harmless;
    # here the same number decides an irreversible rmtree of a directory the
    # harness may still be appending to. A run between two phases has a result
    # for every agent that started, so this is the only check left standing, and
    # `--quiet-for 0` would remove it.
    quiet = max(run.quiet_for, QUIET_FOR)
    age = time.time() - now.last_change
    if age < quiet:
        return False, f"changed {age:.0f} s ago, quiet period {quiet:.0f} s"
    if run.mirror is None or not run.mirror.is_dir():
        return False, "not mirrored yet"
    refused = _aliased(run.source, run.mirror)
    if refused:
        return False, refused
    bad = verify(run)
    if bad:
        # mirror() skips a file whose size and mtime match, so a mirror copy
        # damaged in place would fail here on every run and never be repaired.
        # One re-copy of exactly the mismatched files, then the hash decides.
        for src, dst, name in _plan(run):
            if name in bad:
                shutil.copy2(src, dst)
        bad = verify(run)
    if bad:
        shown = ", ".join(bad[:5]) + (f" (+{len(bad) - 5} more)" if len(bad) > 5 else "")
        return False, f"mirror mismatch: {shown}"
    try:
        shutil.rmtree(run.source)
    except FileNotFoundError:
        return False, "session copy already gone"
    run.source = None
    note = f"moved to {run.mirror.relative_to(root) if run.mirror.is_relative_to(root) else run.mirror}"
    if log is not None:
        log(f"{run.run_id} {note}")
    return True, note


def sync(root: Path, home: Path, *, move: bool = False, quiet_for: float = QUIET_FOR,
         log: Callable[[str], None] | None = None) -> list[SyncResult]:
    """Adopt every run that still has a session copy: copy it into the repo
    and, with `move`, remove the session copy once it verifies.

    This is the path for runs written before the session was linked, or on a
    machine where the hook never ran. Linked runs are already in the repo and
    have no `source`, so they are skipped here; `pf workflow link` is what keeps
    the list empty."""
    out = []
    for run in discover(root, home, quiet_for=quiet_for):
        if run.source is None:
            continue
        try:
            rep = mirror(run, root, log=log)
            moved, note = (False, "")
            if move and not rep.refused:
                moved, note = finalize(run, root, log=log)
        except OSError as exc:  # one run's trouble must not stop the others
            out.append(SyncResult(run.run_id, run.name, 0, 0, False,
                                  f"skipped: {type(exc).__name__}: {exc}"))
            continue
        out.append(SyncResult(run.run_id, run.name, len(rep.copied), rep.bytes, moved, note,
                              rep.refused))
    return out


def watch(root: Path, home: Path, *, interval: float = 2.0, quiet_for: float = QUIET_FOR,
          log: Callable[[str], None] = print, until: Callable[[], bool] | None = None,
          max_rounds: int | None = None) -> None:
    """Follow every run of this repo and print only what changed: a run's
    progress line when its counts moved or its size crossed a SIZE_STEP, one
    line per agent that started or finished. A linked run is read where the
    harness is writing it, so its progress is the run's own file growing; a run
    from an unlinked session is copied in each round first, so watching it also
    adopts it.
    `until` and `max_rounds` exist so a test can drive rounds without sleeping."""
    seen: dict[str, tuple[int, int, int, int]] = {}
    states: dict[str, dict[str, str]] = {}
    rounds = 0
    while True:
        for run in discover(root, home, quiet_for=quiet_for):
            if run.source is not None:
                try:
                    mirror(run, root)
                except OSError as exc:
                    log(f"{run.run_id} mirror skipped this round: {exc}")
                    continue
            key = (run.started, run.finished, run.failed, run.bytes // SIZE_STEP)
            first = run.run_id not in seen
            if seen.get(run.run_id) != key:
                log(run.progress_line())
                seen[run.run_id] = key
            prev = states.setdefault(run.run_id, {})
            for a in run.agents:
                was = prev.get(a.agent_id)
                # On first sight only the agents still running are worth a
                # line; listing every finished one would replay the whole run.
                if was is None and (not first or a.state == "running"):
                    log(f"  ▸ [{a.phase}] {a.label}")
                if was in (None, "running") and a.state != "running" and not first:
                    mark = "✓" if a.state == "done" else "✗"
                    log(f"  {mark} [{a.phase}] {a.label}")
                prev[a.agent_id] = a.state
        rounds += 1
        if until is not None and until():
            return
        if max_rounds is not None and rounds >= max_rounds:
            return
        if interval > 0:
            time.sleep(interval)
