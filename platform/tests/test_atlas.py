"""Tests for the per-project atlas and its dbt hook.

Two things here are easy to get wrong in ways nothing reports.

**The hook must be inert unless asked.** It runs inside every dbt invocation in
the platform, so a hook that fires on the wrong command, in the wrong
directory, or when disabled is a rewrite nobody asked for — and one that raises
turns a successful build into a failed one.

**The config must layer.** Platform, then group, then project, later winning key
by key. A group that switches something on for every sister and a project that
opts out have to be able to coexist, or the setting is not really per project.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pf import atlas

ROOT = Path(__file__).resolve().parents[2]


def _project(tmp_path: Path, group: str = "demo", project: str = "demo-us") -> Path:
    (tmp_path / "groups" / group / "projects" / project / "kg").mkdir(parents=True)
    return tmp_path


def _write(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body)


# ---------------------------------------------------------------- config -----
def test_defaults_apply_when_nothing_is_configured(tmp_path: Path) -> None:
    root = _project(tmp_path)

    cfg = atlas.load_config(root, "demo", "demo-us")

    assert cfg == atlas.DEFAULTS
    assert cfg.phases == ("after_dbt_run",), "the graph is only fresh after a build"


def test_a_group_setting_reaches_every_sister(tmp_path: Path) -> None:
    root = _project(tmp_path)
    _write(root / "groups" / "demo" / "atlas.yaml",
           "atlas:\n  phases: [before_dbt_run, after_dbt_run]\n  keep_previous: true\n")

    cfg = atlas.load_config(root, "demo", "demo-us")

    assert cfg.phases == ("before_dbt_run", "after_dbt_run")
    assert cfg.keep_previous


def test_a_project_overrides_its_group_key_by_key(tmp_path: Path) -> None:
    """The point of layering: opting out without arguing with your siblings."""
    root = _project(tmp_path)
    _write(root / "groups" / "demo" / "atlas.yaml",
           "atlas:\n  phases: [before_dbt_run]\n  keep_previous: true\n")
    _write(root / "groups" / "demo" / "projects" / "demo-us" / "atlas.yaml",
           "atlas:\n  enabled: false\n")

    cfg = atlas.load_config(root, "demo", "demo-us")

    assert not cfg.enabled
    assert cfg.keep_previous, "an override must not reset the keys it did not name"
    assert cfg.phases == ("before_dbt_run",)


def test_an_unknown_key_is_refused_by_name(tmp_path: Path) -> None:
    """Silently ignoring it is how a typo becomes a setting nobody has."""
    root = _project(tmp_path)
    _write(root / "groups" / "demo" / "projects" / "demo-us" / "atlas.yaml",
           "atlas:\n  enabeld: false\n")

    with pytest.raises(atlas.InvalidConfig, match="enabeld"):
        atlas.load_config(root, "demo", "demo-us")


def test_an_unknown_phase_is_refused(tmp_path: Path) -> None:
    root = _project(tmp_path)
    _write(root / "groups" / "demo" / "projects" / "demo-us" / "atlas.yaml",
           "atlas:\n  phases: [after_dbt_seed]\n")

    with pytest.raises(atlas.InvalidConfig, match="after_dbt_seed"):
        atlas.load_config(root, "demo", "demo-us")


def test_the_scaffolded_config_parses_and_matches_the_defaults(tmp_path: Path) -> None:
    """The file a new project is handed must not disagree with the code."""
    root = _project(tmp_path)
    _write(root / "groups" / "demo" / "projects" / "demo-us" / "atlas.yaml",
           atlas.default_yaml())

    assert atlas.load_config(root, "demo", "demo-us") == atlas.DEFAULTS


# ------------------------------------------------------------------ hook -----
def test_the_hook_fires_only_for_run_and_build(tmp_path: Path) -> None:
    """`parse`, `deps` and `ls` change nothing an atlas would show.

    Firing on them would put three identical regenerations in front of every
    real one, on every seed.
    """
    root = _project(tmp_path)
    d = root / "groups" / "demo" / "projects" / "demo-us"

    for cmd in ("parse", "deps", "ls", "debug", "docs"):
        assert atlas.run_phase(d, "after_dbt_run", cmd) is None, cmd
    assert atlas.run_phase(d, "after_dbt_run", "build") is not None


def test_the_hook_respects_the_configured_phase(tmp_path: Path) -> None:
    root = _project(tmp_path)
    d = root / "groups" / "demo" / "projects" / "demo-us"

    assert atlas.run_phase(d, "before_dbt_run", "build") is None, "not a default phase"

    _write(d / "atlas.yaml", "atlas:\n  phases: [before_dbt_run]\n")
    assert atlas.run_phase(d, "before_dbt_run", "build") is not None
    assert atlas.run_phase(d, "after_dbt_run", "build") is None


def test_a_disabled_project_writes_nothing(tmp_path: Path) -> None:
    root = _project(tmp_path)
    d = root / "groups" / "demo" / "projects" / "demo-us"
    _write(d / "atlas.yaml", "atlas:\n  enabled: false\n")

    assert atlas.run_phase(d, "after_dbt_run", "build") is None
    assert atlas.write(root, "demo", "demo-us") is None
    assert not (d / "kg" / "atlas.html").exists()


def test_the_hook_never_raises(tmp_path: Path) -> None:
    """It runs inside `dbt()`. A broken atlas must not fail a build that worked.

    Three ways it could: a path that is not inside a project at all, a config
    that does not parse, and a phase nobody defined.
    """
    assert atlas.run_phase(tmp_path, "after_dbt_run", "build") is None
    assert atlas.run_phase(Path("/nonexistent/x"), "after_dbt_run", "build") is None

    root = _project(tmp_path)
    d = root / "groups" / "demo" / "projects" / "demo-us"
    _write(d / "atlas.yaml", "atlas:\n  phases: [ unclosed\n")
    assert atlas.run_phase(d, "after_dbt_run", "build") is None

    assert atlas.run_phase(d, "sideways", "build") is None


def test_keep_previous_moves_the_outgoing_page_aside(tmp_path: Path) -> None:
    """Otherwise a before/after pair is one file that overwrote itself."""
    root = _project(tmp_path)
    d = root / "groups" / "demo" / "projects" / "demo-us"
    _write(d / "atlas.yaml", "atlas:\n  keep_previous: true\n")

    first = atlas.write(root, "demo", "demo-us")
    first.write_text("<title>the earlier one</title>")
    atlas.write(root, "demo", "demo-us")

    prev = d / "kg" / "atlas.prev.html"
    assert prev.exists()
    assert "the earlier one" in prev.read_text()
    assert "the earlier one" not in first.read_text()


def test_dbt_runtime_calls_the_hook_around_the_run(monkeypatch, tmp_path: Path) -> None:
    """The wiring, not the atlas: `dbt()` is the one funnel every call uses."""
    import subprocess

    from pf.runtime import dbt_runtime

    seen: list[tuple[str, str]] = []
    monkeypatch.setattr(dbt_runtime, "_run_hooks",
                        lambda d, phase, cmd: seen.append((phase, cmd)))
    monkeypatch.setattr(subprocess, "run",
                        lambda *a, **k: subprocess.CompletedProcess(a, 0, "", ""))

    dbt_runtime.dbt(tmp_path, "build")

    assert seen == [("before_dbt_run", "build"), ("after_dbt_run", "build")]

    seen.clear()
    dbt_runtime.dbt(tmp_path, "build", hooks=False)
    assert seen == [], "hooks=False is what stops a hook recursing into dbt"


# ---------------------------------------------------------------- render -----
def test_an_empty_project_still_renders_and_says_why(tmp_path: Path) -> None:
    """Bootstrap runs this on a project with no graph at all."""
    root = _project(tmp_path)

    out = atlas.write(root, "demo", "demo-us")
    page = out.read_text()

    assert "<title>demo-us — project atlas</title>" in page
    assert "pf kg build" in page, "a gap has to name its fix"
    assert "<pre class=\"mermaid\">" in page


def test_every_diagram_declares_the_classes_it_uses(tmp_path: Path) -> None:
    """An undefined class renders as mermaid's default fill and reads as chosen."""
    import re

    root = _project(tmp_path)
    page = atlas.write(root, "demo", "demo-us").read_text()

    blocks = re.findall(r'<pre class="mermaid">(.*?)</pre>', page, re.S)
    assert blocks
    for b in blocks:
        used = set(re.findall(r":::(\w+)", b))
        defined = set(re.findall(r"classDef (\w+)", b))
        assert not used - defined, f"undefined class(es): {sorted(used - defined)}"


def test_labels_are_escaped_for_mermaid() -> None:
    """`<` is the dangerous one: htmlLabels is on, so it is swallowed as a tag.

    An exposure owner written `Finance <fin@x.test>` loses the address — the
    very thing a reader needed — and nothing errors.
    """
    assert atlas.esc("Finance <fin@x.test>") == "Finance #lt;fin@x.test#gt;"
    assert atlas.esc('a "quoted" #hash') == "a #quot;quoted#quot; #35;hash"
    assert atlas.esc("x" * 80).endswith("…")


def test_sections_can_be_trimmed(tmp_path: Path) -> None:
    root = _project(tmp_path)
    cfg = atlas.load_config(root, "demo", "demo-us")

    full = atlas.render(atlas.gather(root, "demo", "demo-us"), cfg)
    trimmed = atlas.render(atlas.gather(root, "demo", "demo-us"),
                           atlas.Config(sections=("census",)))

    assert "provenance" in full
    assert "provenance" not in trimmed
    assert "census" in trimmed


def test_render_is_stable_for_an_unchanged_project(tmp_path: Path) -> None:
    """The page is regenerated on every dbt build; instability would be churn."""
    root = _project(tmp_path)
    cfg = atlas.load_config(root, "demo", "demo-us")

    a = atlas.render(atlas.gather(root, "demo", "demo-us"), cfg)
    b = atlas.render(atlas.gather(root, "demo", "demo-us"), cfg)

    assert a == b


# ------------------------------------------------------------- real repo -----
def _real() -> list[tuple[str, str]]:
    g = ROOT / "groups"
    if not g.exists():
        return []
    return sorted((grp.name, p.name) for grp in g.iterdir() if grp.is_dir()
                  for p in (grp / "projects").iterdir()
                  if (grp / "projects").exists() and p.is_dir()
                  and not p.name.startswith("."))


@pytest.mark.parametrize(("group", "project"), _real(),
                         ids=lambda x: x if isinstance(x, str) else "")
def test_every_real_project_resolves_a_config(group: str, project: str) -> None:
    cfg = atlas.load_config(ROOT, group, project)

    assert set(cfg.phases) <= set(atlas.PHASES)
    assert set(cfg.sections) <= atlas.SECTIONS
    assert cfg.output.endswith(".html")
