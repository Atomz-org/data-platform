"""What a project can have — the vocabulary the architecture map is built from.

This is its own module because three things need the same `Feature` type and
none of them may import the others: `pf.architecture` composes the registry,
`pf.capabilities` lets a capability say what it contributes, and `pf.tools.spec`
lets a tool do the same. It imports nothing from `pf`, deliberately — it is a
vocabulary, not a subsystem.

## Why features are contributed rather than listed

The first version of the architecture map held one hard-coded tuple of features.
That was already the mistake the rest of this platform is built to avoid: a tool
is added by installing a package that advertises a `pf.tools` entry point, and
nothing in this repository is supposed to change when one is. A closed list
breaks that in the worst direction — a third-party tool that writes
`elementary/` into a project would make every project report an unmapped
directory and fail `pf arch --check`, with no way to fix it but a patch to
platform code.

So the registry is composed at call time: the platform's own features, plus
whatever the installed capabilities and tools declare or imply. A capability
that writes files no feature claims contributes one automatically, from what it
already declares — there is nothing extra to write for the common case, and
`Capability.feature` / `Tool.features` are there for the case that wants a
better title than a derivation can produce.

## Why derivation is suppressed for territory already claimed

Almost every capability writes `docs/<name>.md`, and the platform already has a
`capability docs` feature covering `docs/*.md`. Deriving a feature per
capability there would put nine near-identical rows in every map, each saying
"this capability wrote a page". Capabilities and tools are named on their own
summary line instead; a row is earned only by writing somewhere nothing else
accounts for, which is exactly the case that would otherwise show up as an
unmapped directory.
"""

from __future__ import annotations

from dataclasses import dataclass
from fnmatch import fnmatch

#: Reading order, ingest to operate. A lane is a stage of the same pipeline, so
#: the order is the pipeline's, not alphabetical. Contributed features pick one
#: of these rather than inventing a lane, because a lane nobody else uses is a
#: section of one row.
LANES = ("ingest", "transform", "semantics", "governance", "delivery", "operate")


class InvalidFeature(ValueError):
    """A feature declaration that cannot be rendered. Raised at construction."""


@dataclass(frozen=True)
class Feature:
    """One thing a project can have, and how to tell whether it has it.

    Detection is by path glob rather than by asking a subsystem, deliberately:
    a feature must be detectable in a project that cannot import its own code,
    has no warehouse and has never been built. That is the state of every
    project the moment it is scaffolded, and of any project on a CI runner
    without credentials.
    """

    key: str
    title: str
    lane: str
    why: str
    #: Globs relative to the project directory. The first is printed as the
    #: feature's location, so put the most descriptive one first.
    paths: tuple[str, ...] = ()
    #: Globs relative to the repository root, `{project}` and `{group}`
    #: substituted. For artefacts that are about this project but live outside
    #: it — its CI workflow, its Dagster code location.
    repo_paths: tuple[str, ...] = ()
    #: A graph node kind whose count is truer than the file count: one YAML file
    #: can declare six metrics, and "1 file" is the wrong answer. Falls back to
    #: the file count only when there is no graph at all.
    count_kind: str = ""
    #: Absent is a decision, not a gap. Capabilities and tools are opt-in, and a
    #: project without Evidence has not forgotten Evidence.
    optional: bool = False
    #: The command that creates or refreshes it, printed beside every absent row
    #: so a gap is actionable rather than just true.
    made_by: str = ""
    #: This feature *is* the document being written. Detected like any other it
    #: is absent in the render that creates it and present in the next one, so
    #: the file never matches what the project would produce and the drift check
    #: fails forever.
    self_reporting: bool = False
    #: Who contributed it: `platform`, `capability:<name>`, `tool:<name>`. Shown
    #: nowhere; used to explain an unexpected row and to keep derivation from
    #: overwriting a hand-written entry.
    source: str = "platform"

    def __post_init__(self) -> None:
        if self.lane not in LANES:
            raise InvalidFeature(
                f"feature {self.key!r} declares lane {self.lane!r}; "
                f"pick one of {', '.join(LANES)}")
        if not self.key.replace("-", "_").replace(":", "_").isidentifier():
            raise InvalidFeature(f"feature key {self.key!r} is not a usable slug")
        if not (self.paths or self.repo_paths):
            raise InvalidFeature(f"feature {self.key!r} has nothing to detect it by")
        if not self.made_by:
            raise InvalidFeature(
                f"feature {self.key!r} names no command — an absent row has to "
                "say what would create it")

    @property
    def segments(self) -> set[str]:
        """First path segment of each glob — the territory this feature claims."""
        return {g.split("/", 1)[0] for g in self.paths}


#: First path segment to lane, for a contributed feature that does not name one.
#: A heuristic, and a documented one: it is right for everything shipped here,
#: and a tool that lands somewhere unexpected gets `operate` plus the option of
#: saying otherwise.
LANE_BY_PREFIX = {
    "src": "ingest", ".dlt": "ingest", "contracts": "ingest", "data": "ingest",
    "transform": "transform",
    "kg": "semantics", "mdl": "semantics", "catalog": "semantics",
    "governance": "governance", "decisions": "governance", ".claude": "governance",
    "reporting": "delivery", "docs": "delivery",
    "evals": "operate", ".memory": "operate",
}


def lane_for(paths: tuple[str, ...]) -> str:
    for p in paths:
        lane = LANE_BY_PREFIX.get(p.split("/", 1)[0])
        if lane:
            return lane
    return "operate"


def unclaimed(paths: tuple[str, ...], claimed: set[str]) -> tuple[str, ...]:
    """The paths whose territory no existing feature covers.

    Segment-level rather than glob-level, and on purpose: it is the same
    granularity the unmapped check uses, so a derived feature claims exactly
    what would otherwise be reported as a hole and nothing more.
    """
    return tuple(p for p in paths if p.split("/", 1)[0] not in claimed)


def derive(name: str, description: str, paths: tuple[str, ...], *, source: str,
           made_by: str, optional: bool, claimed: set[str],
           lane: str = "") -> Feature | None:
    """A feature for whatever `name` writes that nothing else accounts for.

    Returns None when every path is already covered, which is the common case
    and not a failure — see the module docstring for why nine capabilities that
    each write one documentation page do not deserve nine rows.
    """
    fresh = unclaimed(tuple(paths), claimed)
    if not fresh:
        return None
    # A file path is not a glob. `catalog/ingestion` names a directory the tool
    # fills, and matching it literally would report "1" for any number of files
    # in it, so directories are widened and files are left exact.
    globs = tuple(p if any(c in p for c in "*?[") else
                  (p if "." in p.rsplit("/", 1)[-1] else f"{p}/**") for p in fresh)
    return Feature(
        key=source.replace(":", "_"),
        title=name,
        lane=lane or lane_for(globs),
        why=" ".join(description.split())[:110] or f"contributed by {source}",
        paths=globs,
        optional=optional,
        made_by=made_by,
        source=source,
    )


def covered(path: str, features: tuple[Feature, ...]) -> bool:
    """Does any feature's glob match this exact path? Used by the tests."""
    return any(fnmatch(path, g) for f in features for g in f.paths)
