#!/usr/bin/env python3
"""PostToolUse hook — normalise what the agent just wrote.

Formatting is the one class of review nobody should spend a turn on. This runs
after every successful Edit/Write and leaves the file in repo style.

Three properties it must have, in order:

1. **It never mangles.** It refuses to touch anything the gate denies, anything
   generated, and anything under vendor/ or a virtualenv. For SQL it relies on
   sqlfluff's own refusal to rewrite a file it could not parse — models using
   project macros template to an unparsable tree under the stubbed `jinja`
   templater, and are silently left alone rather than half-formatted.
2. **It is quiet.** A hook that prints on success trains everyone to ignore it.
   The only thing it ever says is that the file it was handed is not valid
   source, which is worth a turn.
3. **It never breaks the session.** Any unexpected failure exits 0.

exit 0 = silent (the normal case)
exit 2 = stderr is shown to the agent (file does not parse)
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

WRITE_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}

# Directories whose contents are not ours to reformat: pinned upstreams, build
# output, installed packages. `target` and `dbt_packages` are dbt artefacts and
# are already on the gate denylist; they are repeated here so the hook is still
# safe if it ever runs somewhere the gate cannot be imported.
SKIP_PARTS = {
    ".git", ".venv", "venv", "site-packages", "node_modules",
    "vendor", "target", "target-base", "dbt_packages", "__pycache__",
    ".evidence", "build", "dist",
}

TIMEOUT = 45


def repo_root(start: Path) -> Path:
    for p in [start, *start.parents]:
        if (p / "platform").is_dir() and (p / "groups").is_dir():
            return p
    return start


def tool(root: Path, name: str) -> list[str] | None:
    """Prefer the workspace venv over PATH.

    `uv run <tool>` would also work but re-resolves the environment on every
    invocation, which is a few hundred milliseconds on a hook that fires after
    every single edit.
    """
    venv = root / ".venv" / "bin" / name
    if venv.exists():
        return [str(venv)]
    found = shutil.which(name)
    return [found] if found else None


def run(cmd: list[str]) -> subprocess.CompletedProcess | None:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT)
    except Exception:
        return None


def gate_blocks(rel: str, root: Path, cwd: Path) -> bool:
    """Ask the same policy the PreToolUse gate asks.

    A denied path reaching this hook means the write happened outside the gate
    (a generator, a capability). Formatting it would create drift against the
    template it came from.
    """
    sys.path.insert(0, str(root / "platform" / "src"))
    try:
        from pf.loops.gate import check_path, project_for
    except Exception:
        return False
    try:
        return bool(check_path(rel, root, in_project=project_for(str(cwd), root) is not None).blocked)
    except Exception:
        return False


def format_python(root: Path, path: Path) -> str | None:
    ruff = tool(root, "ruff")
    if not ruff:
        return None
    fmt = run([*ruff, "format", "--quiet", str(path)])
    if fmt is not None and fmt.returncode != 0:
        # ruff format only fails when it cannot parse the file. That is a real
        # fault in what was just written, and the agent should hear about it.
        return (fmt.stderr or fmt.stdout or "ruff format failed").strip()
    # Import sorting only (`I`), deliberately not a bare `--fix-only`. The full
    # default rule set includes F401, whose fix *deletes* unused imports — and
    # halfway through writing a function the import above it is legitimately
    # still unused. A hook that removes code the agent is about to use is worse
    # than no hook. Everything semantic stays with `ruff check` in review.
    run([*ruff, "check", "--fix-only", "--select", "I", "--quiet", str(path)])
    return None


def format_sql(root: Path, path: Path) -> None:
    # Only dbt model/macro/test SQL. Loose .sql elsewhere (a scratch query, a
    # fixture) is not ours to restyle.
    if "transform" not in path.parts:
        return
    sqlfluff = tool(root, "sqlfluff")
    cfg = root / ".sqlfluff"
    if not sqlfluff or not cfg.exists():
        return
    # --ignore-local-config stops sqlfluff walking to the filesystem root looking
    # for config, which both costs time and crashes outright on a directory the
    # process cannot list.
    run([*sqlfluff, "fix", "--disable-progress-bar", "--ignore-local-config",
         "--config", str(cfg), str(path)])


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0

    if payload.get("tool_name") not in WRITE_TOOLS:
        return 0

    raw = (payload.get("tool_input") or {}).get("file_path") or ""
    if not raw:
        return 0

    path = Path(raw)
    if not path.is_absolute():
        path = Path(payload.get("cwd") or Path.cwd()) / path
    try:
        path = path.resolve()
    except Exception:
        return 0
    if not path.is_file():
        return 0
    if SKIP_PARTS & set(path.parts):
        return 0

    cwd = Path(payload.get("cwd") or Path.cwd()).resolve()
    root = repo_root(cwd)
    try:
        rel = str(path.relative_to(root))
    except ValueError:
        return 0  # outside the repo entirely

    if gate_blocks(rel, root, cwd):
        return 0

    if path.suffix == ".py":
        problem = format_python(root, path)
        if problem:
            print(f"{rel} does not parse — formatting skipped:\n{problem}", file=sys.stderr)
            return 2
    elif path.suffix == ".sql":
        format_sql(root, path)

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)  # a formatter is never a reason to interrupt the session
