"""The context every agent reads agrees with itself, and the graphs stay in bounds.

`GEMINI.md` importing a file that moved, the Copilot file naming an index that
was renamed, a hook pointing at "§5" after `AGENTS.md` was renumbered: each
leaves a tool believing it has been told the rules. These guard the
hand-written layer around the generated context, that `pf context refresh` is
the one-step fix for the generated layer, and that the code graph stops at
`platform/` — the one drift here that fails by *succeeding*, since without its
marker directory the graph spans every sister project instead of erroring.
"""

from __future__ import annotations

import json
from pathlib import Path

from conftest import REPO_ROOT
from pf.agentcontext import ENTRY_POINTS, GENERATED, check, references, refresh, sections
from pf.memory import add


def test_the_entry_points_agree_in_this_repo() -> None:
    """Run `uv run pf context check` for the reason if this fails."""
    assert check(REPO_ROOT) == []


def test_every_generated_artefact_is_current_in_this_repo() -> None:
    """`refresh --dry-run` lists what a fresh regeneration would change; nothing may be stale."""
    stale = [str(p.relative_to(REPO_ROOT)) for p in refresh(REPO_ROOT, dry_run=True)]
    assert stale == [], f"run `uv run pf context refresh`: {stale}"


def test_agents_md_names_everything_the_check_relies_on() -> None:
    text = (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert {0, 1, 2, 3, 4, 5, 6, 7} <= sections(text), "the protocol's numbered sections are what pointers target"
    for f in (*ENTRY_POINTS, *GENERATED):
        if f != "AGENTS.md":
            assert f in text, f"AGENTS.md must name {f}"


def _code_graph_wiring(root: Path) -> None:
    """`check` covers the code graph too, so a conforming tree has its wiring."""
    from pf import codegraph

    marker = f"{codegraph.SCOPE}/{codegraph.MARKER_DIR}"
    codegraph.init(root)
    (root / ".gitignore").write_text(f"{marker}/*\n!{marker}/README.md\n", encoding="utf-8")
    (root / "gate.yaml").write_text(f'denylist:\n  - "{marker}/**"\n', encoding="utf-8")
    (root / ".mcp.json").write_text(
        json.dumps(
            {"mcpServers": {codegraph.MCP_KEY: {"args": [codegraph.MCP_SUBCOMMAND, "--repo", f"/r/{codegraph.SCOPE}"]}}}
        ),
        encoding="utf-8",
    )


def _conforming(tmp_path: Path) -> Path:
    """The smallest tree `check` accepts: every file present, every mention made."""
    root = tmp_path
    (root / "platform").mkdir()
    (root / "groups" / "g" / "projects" / "p").mkdir(parents=True)
    (root / ".github" / "workflows").mkdir(parents=True)
    (root / "platform" / "toolkits" / "power-tools" / "hooks").mkdir(parents=True)
    for m in ("", "platform", "groups/g", "groups/g/projects/p"):
        d = root / m / ".memory" / "notes"
        d.mkdir(parents=True)
        (d / "README.md").write_text("x", encoding="utf-8")
    (root / "CLAUDE.md").write_text("router", encoding="utf-8")
    (root / "AGENTS.md").write_text(
        "# p\n\nCLAUDE.md GEMINI.md .github/copilot-instructions.md\n"
        ".memory/MEMORY.md docs/ARCHITECTURE.md platform/tests/README.md\n"
        "**Session** **Autonomous** **Inline** pf memory add pf context check pf code\n"
        + "".join(f"## {n}. s\n" for n in range(8)),
        encoding="utf-8",
    )
    _code_graph_wiring(root)
    (root / "GEMINI.md").write_text("see §0\n\n@./CLAUDE.md\n\n@./AGENTS.md\n", encoding="utf-8")
    (root / ".github" / "copilot-instructions.md").write_text(
        "CLAUDE.md AGENTS.md .memory/MEMORY.md §3 §4 §5", encoding="utf-8"
    )
    (root / ".github" / "workflows" / "claude.yml").write_text("PF_AGENT: x\nAGENTS.md section 4", encoding="utf-8")
    (root / ".github" / "workflows" / "copilot-setup-steps.yml").write_text(
        "copilot-setup-steps:\n pf memory check", encoding="utf-8"
    )
    (root / "platform" / "toolkits" / "power-tools" / "hooks" / "session_start.sh").write_text(
        "AGENTS.md §5 pf memory show", encoding="utf-8"
    )
    return root


def test_a_conforming_tree_passes_and_each_drift_is_named(tmp_path: Path) -> None:
    root = _conforming(tmp_path)
    assert check(root) == []

    (root / "GEMINI.md").write_text("see §9\n\n@./CLAUDE.md\n\n@./AGENTS.md\n", encoding="utf-8")
    [problem] = check(root)
    assert "GEMINI.md" in problem and "§9" in problem and "renumbered" in problem

    (root / "GEMINI.md").write_text("@./CLAUDE.md\n", encoding="utf-8")
    [problem] = check(root)
    assert "GEMINI.md" in problem and "@./AGENTS.md" in problem

    (root / "GEMINI.md").unlink()
    [problem] = check(root)
    assert problem.startswith("GEMINI.md is missing")


def test_one_command_covers_the_code_graph_wiring_too(tmp_path: Path) -> None:
    """`pf context check` is the single command; it must not miss a graph that
    silently widens to every sister project."""
    from pf import codegraph

    root = _conforming(tmp_path)
    codegraph.marker_readme(root).unlink()
    [problem] = check(root)
    assert "widens" in problem, "the context check must surface code-graph drift"


def test_a_module_without_its_readme_is_named(tmp_path: Path) -> None:
    root = _conforming(tmp_path)
    (root / "groups" / "g" / ".memory" / "notes" / "README.md").unlink()
    [problem] = check(root)
    assert problem.startswith("groups/g:") and "pf context refresh" in problem


def test_section_references_are_read_in_both_spellings() -> None:
    assert references("see §0, § 3 and section 5; Section 12 too") == {0, 3, 5, 12}
    assert sections("## 0. a\n## 7. b\n### 9. not a section\n") == {0, 7}


def test_the_code_graph_wiring_is_true_in_this_repo() -> None:
    """Run `uv run pf code check` for the reason if this fails."""
    from pf import codegraph

    assert codegraph.check(REPO_ROOT) == []


def test_the_code_graph_command_line_always_names_the_scope_and_a_pin() -> None:
    """`--repo` is passed on every call, so a command run from inside a project
    cannot resolve a wider root; the version is pinned, so one tool runs."""
    from pf import codegraph

    cmd = codegraph.argv("impact", "src/pf/cli.py", root=REPO_ROOT)
    assert cmd[0] == "uvx"
    assert cmd[1] == f"{codegraph.PACKAGE}@{codegraph.PINNED}"
    assert cmd[2] == "impact"
    repo = cmd[cmd.index("--repo") + 1]
    assert repo.endswith(f"/{codegraph.SCOPE}"), f"scope must be platform/, got {repo}"
    assert "groups" not in repo
    bare = codegraph.argv("status")
    assert bare[bare.index("--repo") + 1] == codegraph.SCOPE


def test_the_marker_is_ignored_denied_and_excepted_consistently() -> None:
    """`.gitignore` and `gate.yaml` must agree: the database is neither carried
    nor hand-edited, and the README is both tracked and allowed."""
    from pf import codegraph

    ignored = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
    gate = (REPO_ROOT / "gate.yaml").read_text(encoding="utf-8")
    marker = f"{codegraph.SCOPE}/{codegraph.MARKER_DIR}"
    assert f"{marker}/*" in ignored
    assert f"!{marker}/README.md" in ignored
    assert f'"{marker}/**"' in gate
    assert f'"{marker}/README.md"' in gate
    assert codegraph.marker_readme(REPO_ROOT).exists()
    servers = json.loads((REPO_ROOT / ".mcp.json").read_text(encoding="utf-8"))["mcpServers"]
    args = servers[codegraph.MCP_KEY]["args"]
    assert codegraph.MCP_SUBCOMMAND in args
    assert args[args.index("--repo") + 1].endswith(f"/{codegraph.SCOPE}")


def _code_tree(tmp_path: Path) -> Path:
    """The smallest tree the code-graph check accepts."""
    (tmp_path / "AGENTS.md").write_text("ask `pf code impact`\n", encoding="utf-8")
    _code_graph_wiring(tmp_path)
    return tmp_path


def test_each_way_the_code_graph_wiring_breaks_is_named(tmp_path: Path) -> None:
    from pf import codegraph

    root = _code_tree(tmp_path)
    assert codegraph.check(root) == []
    marker = f"{codegraph.SCOPE}/{codegraph.MARKER_DIR}"

    codegraph.marker_readme(root).unlink()
    [problem] = codegraph.check(root)
    assert "widens" in problem and "sisters included" in problem
    codegraph.init(root)

    (root / ".gitignore").write_text("unrelated\n", encoding="utf-8")
    [problem] = codegraph.check(root)
    assert ".gitignore" in problem and "build output" in problem

    # The mistake that deletes the marker from every clone.
    (root / ".gitignore").write_text(f"{marker}/\n", encoding="utf-8")
    [problem] = codegraph.check(root)
    assert "re-including README.md" in problem
    (root / ".gitignore").write_text(f"{marker}/*\n!{marker}/README.md\n", encoding="utf-8")

    (root / "gate.yaml").write_text("denylist: []\n", encoding="utf-8")
    [problem] = codegraph.check(root)
    assert "gate.yaml" in problem
    (root / "gate.yaml").write_text(f'denylist:\n  - "{marker}/**"\n', encoding="utf-8")

    (root / "AGENTS.md").write_text("nothing about the graph\n", encoding="utf-8")
    [problem] = codegraph.check(root)
    assert "AGENTS.md" in problem, "a tool no entry point names is a tool no agent uses"


def test_an_unscoped_mcp_server_is_named(tmp_path: Path) -> None:
    """An agent's tools must see the same boundary the CLI does."""
    from pf import codegraph

    root = _code_tree(tmp_path)
    mcp = root / ".mcp.json"

    mcp.write_text(json.dumps({"mcpServers": {}}), encoding="utf-8")
    [problem] = codegraph.check(root)
    assert "server" in problem and "no agent gets" in problem

    mcp.write_text(json.dumps({"mcpServers": {codegraph.MCP_KEY: {"args": ["serve"]}}}), encoding="utf-8")
    [problem] = codegraph.check(root)
    assert "--repo" in problem and "every sister project" in problem

    mcp.write_text(
        json.dumps({"mcpServers": {codegraph.MCP_KEY: {"args": ["serve", "--repo", "/r"]}}}),
        encoding="utf-8",
    )
    [problem] = codegraph.check(root)
    assert "does not scope --repo" in problem

    mcp.write_text("{not json", encoding="utf-8")
    assert any("does not parse" in p for p in codegraph.check(root))


def test_built_means_a_database_not_just_the_marker(tmp_path: Path) -> None:
    """A marker with only its README is wiring, not a graph. `init` never overwrites."""
    from pf import codegraph

    assert codegraph.init(tmp_path) == [codegraph.marker_readme(tmp_path)]
    assert not codegraph.built(tmp_path)
    (codegraph.marker_dir(tmp_path) / "graph.db").write_bytes(b"x")
    assert codegraph.built(tmp_path)
    codegraph.marker_readme(tmp_path).write_text("mine", encoding="utf-8")
    assert codegraph.init(tmp_path) == []
    assert codegraph.marker_readme(tmp_path).read_text(encoding="utf-8") == "mine"


def test_refresh_writes_the_missing_pieces_and_then_nothing(tmp_path: Path) -> None:
    """Dry run names what is stale; a real run writes exactly that; a second run is a no-op."""
    root = _conforming(tmp_path)
    (root / "groups" / "g" / ".memory" / "notes" / "README.md").unlink()
    add(root, "platform", "a-note", "one line", agent="t")
    (root / ".memory" / "MEMORY.md").unlink()
    would = {p.relative_to(root).as_posix() for p in refresh(root, dry_run=True)}
    assert would == {"groups/g/.memory/notes/README.md", ".memory/MEMORY.md"}
    assert not (root / ".memory" / "MEMORY.md").exists(), "dry run writes nothing"
    did = {p.relative_to(root).as_posix() for p in refresh(root)}
    assert did == would
    assert refresh(root, dry_run=True) == []
