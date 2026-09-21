"""Code graph — the structure of the shared engine, for agents that ask before reading.

`pf kg` models the *data*: Models, Columns, Metrics, Sources, Exposures,
Concepts. It has no notion of which Python function calls which, so a change
under `platform/src/pf/` has no blast radius the way a change to a dbt model
does — an agent editing an engine finds its callers by grep. This fills that
one gap and nothing else. Questions about models, columns, metrics and lineage
still go to `pf kg` and the `pf` MCP server, which answer them far better than
a call graph can.

The tool is `code-review-graph`, pinned under `vendor/` for provenance and
drift (`platform/src/pf/vendor/registry.yaml`) and *run* from its published
wheel through `uvx` — the same shape as the `graphify` entry already in
`.mcp.json`, and for the same reason: its dependency set (fastmcp,
tree-sitter-language-pack, networkx, watchdog) is not one this workspace's
lockfile should have to resolve against dbt, dlt, Dagster and recce. Nothing
here imports it. When `uvx` is absent every command says so and exits 1,
which is the `pf tool doctor` convention: a tool degrades to "not installed"
rather than failing the build.

SCOPE IS THE POINT. The graph's root is `platform/`, never the repository:

    platform/.code-review-graph/            the marker that makes it the root
    platform/.code-review-graph/README.md   tracked, so the directory exists in a clone
    platform/.code-review-graph/<db>        the graph — gitignored and gate-denied

The tool resolves `--repo` by walking *up* from that path for a
`.code-review-graph`, `.git` or `.svn` marker. With the marker in place,
`--repo platform` stops at `platform/`. Without it the walk reaches the
repository's own `.git`, and the graph silently widens to every sister
project and ~27,000 vendored files: a blast radius nobody can read, built by
crossing the one boundary this platform does not allow ("never read another
group or another sister project"). The marker is therefore load-bearing, it
is tracked on purpose, and `check()` fails without it.

`platform/` is also the only module where a single repo-wide graph is safe at
all, because it has no sisters. A project's code is reachable from its own
session and nowhere else; that rule is enforced by `.claude/settings.json`,
mirrored by the memory layout, and would be broken by one graph spanning
`groups/`.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

#: The directory whose presence makes `platform/` the graph's root.
MARKER_DIR = ".code-review-graph"

#: The one module a single code graph may span. See the docstring.
SCOPE = "platform"

#: Run, not imported. Pinned: the repository pins what it runs, and an
#: unpinned `uvx` invocation is a different tool on a different day.
PACKAGE = "code-review-graph"
PINNED = "2.3.9"

#: The MCP server key in `.mcp.json`, and the command that serves it.
MCP_KEY = "code-review-graph"
MCP_SUBCOMMAND = "serve"

MARKER_README = """\
# Code graph marker

This directory makes `platform/` the root of the code graph, and that is its
whole job. `code-review-graph` resolves `--repo` by walking up for a
`.code-review-graph`, `.git` or `.svn` marker: with this directory,
`--repo platform` stops here; without it the walk reaches the repository's
`.git` and the graph widens to every sister project and all of `vendor/`.

It is tracked — README and all — because an empty directory is invisible to a
clone, and a clone without it builds the wrong graph without saying so.

    uv run pf code build          # first build, ~10s for this tree
    uv run pf code impact <file>  # callers, dependents, tests that cover it
    uv run pf code check          # is the wiring still true?

The graph database itself is build output: gitignored, gate-denied, never
committed. Rebuild it rather than carrying it.

Questions about models, columns, metrics or lineage do not belong here. Those
are `pf kg` and the `pf` MCP server, which answer them from the data graph.
"""


# ---------------------------------------------------------------- layout ---
def scope_dir(root: str | Path) -> Path:
    return Path(root) / SCOPE


def marker_dir(root: str | Path) -> Path:
    return scope_dir(root) / MARKER_DIR


def marker_readme(root: str | Path) -> Path:
    return marker_dir(root) / "README.md"


def built(root: str | Path) -> bool:
    """Is there a graph database under the marker? Any file but the README."""
    d = marker_dir(root)
    if not d.is_dir():
        return False
    return any(p.name.lower() != "readme.md" and p.is_file() for p in d.iterdir())


# --------------------------------------------------------------- running ---
def available() -> bool:
    """Can the tool be run at all? `uvx` fetches and runs the pinned wheel."""
    return shutil.which("uvx") is not None


def argv(subcommand: str, *args: str, root: str | Path | None = None) -> list[str]:
    """The exact command line, with the scope always spelled out.

    `--repo` is passed explicitly on every call rather than relying on the
    marker plus the current directory: a command run from inside a project
    would otherwise resolve a different root, and the failure would be a
    quietly wider graph rather than an error.
    """
    repo = str(scope_dir(root)) if root is not None else SCOPE
    return ["uvx", f"{PACKAGE}@{PINNED}", subcommand, "--repo", repo, *args]


def plan(root: str | Path) -> list[str]:
    """What a first run looks like, as copyable lines."""
    return [
        " ".join(argv("build", root=root)),
        " ".join(argv("postprocess", root=root)),
        " ".join(argv("status", root=root)),
    ]


# ----------------------------------------------------------------- wiring ---
def check(root: str | Path) -> list[str]:
    """Every way the code-graph wiring can be wrong, one line each with the fix.

    Only *our* files. Whether the pin is initialised is `pf vendor verify`'s
    job, and whether the tool is installed is a runtime fact, not drift.
    """
    root = Path(root)
    problems: list[str] = []

    if not marker_readme(root).exists():
        problems.append(
            f"{SCOPE}/{MARKER_DIR}/README.md is missing — without the marker the graph "
            f"widens from {SCOPE}/ to the whole repository, sisters included; "
            f"run `pf code init`"
        )

    gitignore = root / ".gitignore"
    ignored = gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""
    if f"{SCOPE}/{MARKER_DIR}/" not in ignored:
        problems.append(
            f".gitignore does not ignore {SCOPE}/{MARKER_DIR}/ — the graph database is "
            f"build output and must never be committed"
        )
    elif f"!{SCOPE}/{MARKER_DIR}/README.md" not in ignored:
        problems.append(
            f".gitignore ignores {SCOPE}/{MARKER_DIR}/ without re-including README.md — "
            f"the marker directory would vanish from a clone"
        )

    gate = root / "gate.yaml"
    gate_text = gate.read_text(encoding="utf-8") if gate.exists() else ""
    if f"{SCOPE}/{MARKER_DIR}/**" not in gate_text:
        problems.append(
            f"gate.yaml does not deny {SCOPE}/{MARKER_DIR}/** — every other generated "
            f"artefact is denied there, and `pf check` compares the two lists"
        )

    mcp = root / ".mcp.json"
    if not mcp.exists():
        problems.append(".mcp.json is missing — agents would get no graph tools at all")
    else:
        try:
            servers = json.loads(mcp.read_text(encoding="utf-8")).get("mcpServers", {})
        except json.JSONDecodeError as exc:
            problems.append(f".mcp.json does not parse ({exc}) — no MCP server starts")
            servers = {}
        entry = servers.get(MCP_KEY)
        if entry is None:
            problems.append(
                f".mcp.json has no `{MCP_KEY}` server — `pf code` works but no agent gets "
                f"the tools; add it or drop the wiring"
            )
        else:
            joined = " ".join(str(a) for a in entry.get("args", []))
            if "--repo" not in joined:
                problems.append(
                    f".mcp.json's `{MCP_KEY}` server passes no --repo — the server would "
                    f"resolve the repository root and index every sister project"
                )
            elif SCOPE not in joined:
                problems.append(
                    f".mcp.json's `{MCP_KEY}` server does not scope --repo to {SCOPE}/ — "
                    f"that is the boundary, not a default"
                )

    protocol = root / "AGENTS.md"
    if protocol.exists() and "pf code" not in protocol.read_text(encoding="utf-8"):
        problems.append(
            "AGENTS.md does not name `pf code` — a tool no entry point mentions is a tool "
            "no agent uses; add it to the read protocol"
        )
    return problems


def init(root: str | Path) -> list[Path]:
    """Create the marker and its README. Idempotent; never overwrites."""
    p = marker_readme(root)
    if p.exists():
        return []
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(MARKER_README, encoding="utf-8")
    return [p]
