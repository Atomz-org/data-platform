"""The context every agent reads agrees with itself, and the graphs stay in bounds.

`GEMINI.md` importing a file that moved, the Copilot file naming an index that
was renamed, a hook pointing at "§5" after `AGENTS.md` was renumbered: each
leaves a tool believing it has been told the rules. These guard the
hand-written layer around the generated context, that `pf context refresh` is
the one-step fix for the generated layer, and that the code graph stops at
`platform/` — the one drift here that fails by *succeeding*, since without its
marker directory the graph spans every sister project instead of erroring.

The onboarding guide is one of the generated pieces, and it is also published
away from the repository, where a stylesheet from the wrong host or a script
of any kind renders as a blank page with no error. Its publish contract is
a section here, a test rather than a note.

The per-scope harness maps are the last section. They are generated from the
files that enforce what they say — a project's settings, the gate, the hooks,
its workflow, its loops — and every gate verdict in them is computed by the
function the PreToolUse hook calls. The tests hold them to that: the map must
say what those files say, must report the gate as it fires rather than as it
is written, must be byte-stable between a laptop and a runner, and must not
grow past the budget that keeps reading it cheaper than reading the tree.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from conftest import REPO_ROOT
from pf import harnessmap
from pf.agentcontext import ENTRY_POINTS, GENERATED, check, references, refresh, sections
from pf.archmap import Facts
from pf.guide import (
    EXTERNAL_HOSTS,
    TITLE,
    GroupRow,
    Guide,
    ProjectRow,
    drift,
    gather,
    render_html,
    render_markdown,
)
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
        ".memory/MEMORY.md docs/ARCHITECTURE.md docs/ONBOARDING.md platform/tests/README.md docs/HARNESSES.md\n"
        "HARNESS.md pf harness\n"
        "**Session** **Autonomous** **Inline** pf memory add pf context check pf code\n"
        + "".join(f"## {n}. s\n" for n in range(8)),
        encoding="utf-8",
    )
    _code_graph_wiring(root)
    # The harness configs are generated from the `.mcp.json` the wiring just
    # wrote; a conforming tree has them current, the way it has its indexes.
    from pf import harness

    harness.write_all(root)
    # The per-scope harness maps likewise: the tree has a group and a project,
    # so a conforming one has their maps, current.
    harnessmap.write(root)
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


def test_a_path_outside_the_platform_is_refused_not_answered(tmp_path: Path) -> None:
    """An empty blast radius for a sister's file would be a wrong answer, not
    a missing one, so the question is refused instead."""
    from pf import codegraph

    scope = codegraph.scope_dir(tmp_path)
    (scope / "src").mkdir(parents=True)
    (scope / "src" / "engine.py").write_text("x", encoding="utf-8")
    (tmp_path / "groups" / "g" / "projects" / "p").mkdir(parents=True)
    sister = tmp_path / "groups" / "g" / "projects" / "p" / "model.py"
    sister.write_text("x", encoding="utf-8")

    # Both spellings of an in-scope path resolve to the same absolute file.
    from_root = codegraph.resolve_scoped(tmp_path, ["platform/src/engine.py"])
    from_inside = codegraph.resolve_scoped(tmp_path, ["src/engine.py"])
    assert from_root == from_inside == [str((scope / "src" / "engine.py").resolve())]

    for bad in (str(sister), "groups/g/projects/p/model.py", "../elsewhere.py"):
        try:
            codegraph.resolve_scoped(tmp_path, [bad])
        except ValueError as exc:
            assert "not under platform/" in str(exc)
        else:
            raise AssertionError(f"{bad} should be refused")


def test_the_blast_radius_is_summarised_to_the_files_to_read() -> None:
    """The answer is which files to open. The tool's own payload for the same
    question is ~13k tokens; this is the reason the default is not that."""
    from pf import codegraph

    scope = codegraph.scope_dir(REPO_ROOT)
    payload = {
        "changed_nodes": [1, 2],
        "total_impacted": 7,
        "impacted_files": [
            str(scope / "src" / "pf" / "cli.py"),
            {"file_path": str(scope / "tests" / "gate" / "test_cli.py")},
            "src/pf/memory.py",
        ],
        "truncated": True,
        "edges_omitted": 176,
    }
    lines = codegraph.summarise_impact(payload, REPO_ROOT)
    assert lines[0] == "2 changed node(s) · 7 impacted · 3 file(s) to read"
    assert "  platform/src/pf/cli.py" in lines
    assert "  platform/src/pf/memory.py" in lines, "a relative path is passed through"
    assert "  platform/tests/gate/test_cli.py  (test)" in lines, "tests are marked and sorted last"
    assert any("176 edge(s) omitted" in ln for ln in lines)
    assert len(" ".join(lines)) // 4 < 60, "the summary is the cheap surface; keep it cheap"


def test_an_unguarded_blast_radius_says_so() -> None:
    """No covering test is the finding, not a silence."""
    from pf import codegraph

    lines = codegraph.summarise_impact(
        {"changed_nodes": [1], "total_impacted": 1, "impacted_files": ["src/pf/engine.py"]}, REPO_ROOT
    )
    assert any("no test covers this" in ln for ln in lines)
    covered = codegraph.summarise_impact(
        {"changed_nodes": [1], "total_impacted": 1, "impacted_files": ["tests/test_x.py"]}, REPO_ROOT
    )
    assert not any("no test covers" in ln for ln in covered)


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


# --------------------------------------------------------- the guide -------
_EXTERNAL = re.compile(r'(?:src|href)="https?://([^/"]+)')


def test_the_committed_guide_matches_the_repository() -> None:
    """Run `uv run pf guide build` if this fails — the repository is the source."""
    assert drift(REPO_ROOT) == ""


def test_the_guide_is_rendered_deterministically() -> None:
    """Compared byte for byte, so two gathers must render the same page.

    Set iteration order is the usual way this breaks, and it breaks
    intermittently — the worst failure mode for something that gates a build.
    """
    a, b = gather(REPO_ROOT), gather(REPO_ROOT)
    assert render_markdown(a) == render_markdown(b)
    assert render_html(a) == render_html(b)


def test_both_renderings_name_every_group_project_step_and_command() -> None:
    """The facts a newcomer acts on must be in both pages, not just the one that was checked."""
    g = gather(REPO_ROOT)
    md, page = render_markdown(g), render_html(g)
    assert g.groups and g.steps and g.commands and g.command_groups, "gather found nothing to say"
    for gr in g.groups:
        for text in (md, page):
            assert f"`{gr.name}`" in text or f"<code>{gr.name}</code>" in text
            for p in gr.projects:
                assert f"{gr.name}/{p.name}" in text
    for name, _why in g.steps:
        assert name in md and name in page
    for name, _help in g.commands:
        assert f"pf {name}" in md and f"pf {name}" in page
    for name, _help in g.command_groups:
        assert f"pf {name}" in md and f"pf {name}" in page


def test_the_html_page_keeps_to_the_publish_contract() -> None:
    """What the page needs to render where it is published, with no error shown when it does not."""
    page = render_html(gather(REPO_ROOT))
    assert f"<title>{TITLE}</title>" in page[:8000], "the title must sit in the first 8KB"
    assert "<script" not in page, "the page needs no script, and a blocked one renders blank"
    hosts = set(_EXTERNAL.findall(page))
    assert hosts <= EXTERNAL_HOSTS, f"off-allowlist host(s): {sorted(hosts - EXTERNAL_HOSTS)}"
    # Theme tokens: the full light palette on bare :root, redefined for the
    # un-stamped dark state and again for the explicit toggle.
    assert re.search(r":root\s*\{[^}]*--paper:", page)
    assert ':root:not([data-theme="light"])' in page
    assert ':root[data-theme="dark"]' in page
    assert re.search(r"body\s*\{[^}]*background: var\(--paper\)", page)
    assert "<!-- snapshot -->" in page, "the publish step stamps the commit here"


def test_the_markdown_has_no_date_or_commit() -> None:
    """A timestamp would make every commit a stale one."""
    md = render_markdown(gather(REPO_ROOT))
    assert not re.search(r"\b20\d\d-\d\d-\d\d\b", md)
    assert not re.search(r"\b[0-9a-f]{40}\b", md)


def test_what_the_repository_says_is_escaped_in_the_html() -> None:
    """A group's display name is data; the page must never execute it."""
    g = Guide(
        facts=Facts(groups={"g": ["p"]}),
        groups=[GroupRow("g", "<img src=x onerror=alert(1)>", "d", "active", (ProjectRow("p", 1, 2, 3, 4),))],
        commands=[("x", "does <b>things</b>")],
    )
    page = render_html(g)
    assert "<img src=x" not in page
    assert "&lt;img src=x onerror=alert(1)&gt;" in page
    assert "does &lt;b&gt;things&lt;/b&gt;" in page


def test_the_checker_can_fail(tmp_path: Path) -> None:
    """A checker that cannot fail is a checker nobody should trust."""
    assert "pf guide build" in drift(tmp_path)
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "ONBOARDING.md").write_text("stale\n", encoding="utf-8")
    (tmp_path / "docs" / "onboarding.html").write_text("stale\n", encoding="utf-8")
    assert "is stale" in drift(tmp_path)


# ---------------------------------------------------- the harness maps -------
def _first_scope(kind: str) -> harnessmap.Scope | None:
    return next((s for s in harnessmap.scopes(REPO_ROOT) if s.kind == kind), None)


def test_every_committed_harness_map_matches_its_scope() -> None:
    """Run `uv run pf harness build` if this fails — the settings, the gate and the workflows are the source."""
    assert [str(d) for d in harnessmap.drift(REPO_ROOT) if not d.ok] == []


def test_the_harness_maps_are_byte_stable_and_carry_no_machine_fact() -> None:
    """Compared byte for byte between a laptop and a runner, so nothing local may leak in.

    No date, no commit, no absolute path: each would make every commit a stale
    one, or make the check pass here and fail on the runner.
    """
    for s in harnessmap.scopes(REPO_ROOT):
        page = s.render(REPO_ROOT)
        assert page == s.render(REPO_ROOT), s.label
        assert not re.search(r"\b20\d\d-\d\d-\d\d\b", page), s.label
        assert not re.search(r"\b[0-9a-f]{40}\b", page), s.label
        assert str(REPO_ROOT) not in page and "/Users/" not in page and "/home/" not in page, s.label


def test_a_project_map_says_what_its_settings_gate_workflow_and_loops_say() -> None:
    """Every fact an agent acts on is in the map: each deny rule, the hook, each tool, job and loop."""
    scope = _first_scope("project")
    if scope is None:
        return
    p = harnessmap.gather_project(REPO_ROOT, scope.group, scope.project)
    page = harnessmap.render_project(p)
    settings = json.loads((p.pdir / ".claude" / "settings.json").read_text(encoding="utf-8"))
    for rule in settings["permissions"]["deny"]:
        assert f"`{rule}`" in page, rule
    for h in p.hooks:
        assert f"`{h.script}`" in page, h.script
    for t in p.tools:
        assert f"`{t.name}`" in page, t.name
    for j in p.jobs:
        assert f"`{j.name}`" in page, j.name
    for lp in p.loops:
        assert f"`{lp.name}`" in page, lp.name
    assert "| `HARNESS.md` |" in page, "the map judges its own path"


def test_the_map_reports_the_gate_as_it_fires_not_as_it_is_written() -> None:
    """A verdict is `check_path`'s, so an allowlist that shadows an impact rule is a named gap, not a promise."""
    from pf.loops.gate import check_path

    scope = _first_scope("project")
    if scope is None:
        return
    p = harnessmap.gather_project(REPO_ROOT, scope.group, scope.project)
    for v in p.verdicts:
        live = check_path(v.path, REPO_ROOT, in_project=True)
        assert (v.verdict, v.rule) == (live.verdict, live.rule), v.path
    shadowed = [v for v in p.verdicts if v.rule.startswith("allowlist:") and harnessmap._impact_on_paper(v.path, p)]
    if shadowed:
        assert any("Impact-gated on paper" in g for g in p.gaps)


def test_the_harness_maps_stay_inside_their_budget() -> None:
    """On-demand tier: cheaper to read than the tree it describes, or it stops being read."""
    from pf.kg.card import estimate_tokens

    for s in harnessmap.scopes(REPO_ROOT):
        n = estimate_tokens(s.render(REPO_ROOT))
        assert n <= harnessmap.HARNESS_BUDGET, f"{s.label}: ~{n} tokens — cap a section rather than the budget"


def test_a_bare_project_renders_and_names_what_it_lacks(tmp_path: Path) -> None:
    """The state at scaffold time — no settings, no graph, no workflow — is a list of named gaps, not a crash."""
    (tmp_path / "groups" / "demo" / "projects" / "demo-us").mkdir(parents=True)
    p = harnessmap.gather_project(tmp_path, "demo", "demo-us")
    page = harnessmap.render_project(p)
    assert "# demo-us — harness" in page
    joined = " ".join(p.gaps)
    for needle in (
        "No edit gate",
        "No `power-tools` plugin",
        "Sisters are readable",
        "No knowledge graph",
        "No CI workflow",
    ):
        assert needle in joined, needle
    assert "# demo — harness" in harnessmap.render_group(harnessmap.gather_group(tmp_path, "demo"))


def test_the_report_map_splits_generated_from_owned() -> None:
    """What `pf report build` rewrites is never listed as yours, and the index and metric pages are its."""
    scope = _first_scope("report")
    if scope is None:
        return
    r = harnessmap.gather_report(REPO_ROOT, scope.group, scope.project)
    page = harnessmap.render_report(r)
    assert "`queries/metrics/*.sql`" in page and "`pages/index.md`, `pages/metrics/*.md`" in page
    assert "pages/index.md" not in r.owned
    assert not any(o.startswith("pages/metrics/") for o in r.owned)
    for o in r.owned:
        assert f"`{o}`" in page, o


def test_the_harness_checker_can_fail(tmp_path: Path) -> None:
    """A checker that cannot fail is a checker nobody should trust."""
    (tmp_path / "groups" / "demo" / "projects" / "demo-us").mkdir(parents=True)
    assert all(d.missing for d in harnessmap.drift(tmp_path)) and len(harnessmap.drift(tmp_path)) == 2
    harnessmap.write(tmp_path)
    assert all(d.ok for d in harnessmap.drift(tmp_path))
    (tmp_path / "groups" / "demo" / "HARNESS.md").write_text("stale\n", encoding="utf-8")
    [stale] = [d for d in harnessmap.drift(tmp_path) if not d.ok]
    assert stale.scope.kind == "group" and "stale" in str(stale) and "would render" in str(stale)
