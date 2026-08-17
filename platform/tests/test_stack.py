"""The control plane's generated configuration.

Everything `pf stack render` writes is derived from the project roster, and all
of it fails *quietly* when it is wrong: a missing `search_path` puts Dagster's
tables in OpenMetadata's schema and nothing complains until the next upgrade; a
`/api/` block that outranks `/api/v1/` hands OpenMetadata's REST API to recce
and the catalogue simply goes blank. Neither shows up in a smoke test that only
checks the process came up.

So these assert the two or three characters in each generated file that carry
the whole design, rather than the files' shape.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pf.stack import frontdoor, storage

BASE_YAML = """\
# Dagster instance config.
telemetry:
  enabled: false

concurrency:
  pools:
    granularity: op
    default_limit: 1
"""


def roster(tmp_path: Path, *names: tuple[str, str],
           dbt: bool = True, defs: bool = True) -> list[tuple[str, str, Path]]:
    """A fake `all_projects()` on disk, since both builders stat the tree."""
    out = []
    for group, project in names:
        d = tmp_path / "groups" / group / "projects" / project
        if dbt:
            (d / "transform").mkdir(parents=True, exist_ok=True)
            (d / "transform" / "dbt_project.yml").write_text("name: x\n")
        if defs:
            module = project.replace("-", "_")
            (d / "src" / module).mkdir(parents=True, exist_ok=True)
            (d / "src" / module / "definitions.py").write_text("defs = None\n")
        d.mkdir(parents=True, exist_ok=True)
        out.append((group, project, d))
    return out


# ----------------------------------------------------------------- storage --
def test_the_storage_block_scopes_dagster_to_its_own_schema() -> None:
    """The one parameter separating two products in one database."""
    block = storage.storage_block(storage.Settings(host="pg"))
    assert "options: -c search_path=dagster" in block


def test_the_block_names_the_password_and_never_carries_it() -> None:
    s = storage.Settings(host="pg", password="hunter2")
    merged, _ = storage.merge_storage(BASE_YAML, s)

    assert "hunter2" not in merged
    assert f"env: {storage.ENV_PASSWORD}" in merged
    # A traceback prints the frame's locals, and a connection failure is when
    # this object gets printed.
    assert "hunter2" not in repr(s)
    assert "hunter2" not in f"{s}"


def test_merging_is_idempotent_and_reversible() -> None:
    """`pf stack render` runs on every container start, on a tracked file."""
    s = storage.Settings(host="pg")

    once, first = storage.merge_storage(BASE_YAML, s)
    twice, second = storage.merge_storage(once, s)
    removed, third = storage.merge_storage(twice, None)

    assert first and not second and third
    assert removed == BASE_YAML
    # The hand-written part survives verbatim; that is the point of splicing.
    assert "default_limit: 1" in once


def test_no_host_means_sqlite_rather_than_a_block_pointing_nowhere() -> None:
    """A dagster.yaml naming an unreachable Postgres fails at import."""
    assert storage.settings({}) is None
    assert storage.settings({storage.ENV_HOST: "   "}) is None

    s = storage.settings({storage.ENV_HOST: "pg", storage.ENV_PORT: "6000"})
    assert s is not None and s.port == 6000


def test_a_non_numeric_port_falls_back_rather_than_raising() -> None:
    s = storage.settings({storage.ENV_HOST: "pg", storage.ENV_PORT: "auto"})
    assert s is not None and s.port == storage.DEFAULT_PORT


def test_the_dsn_carries_the_schema_urlencoded() -> None:
    s = storage.Settings(host="pg", schema="dagster")
    assert "options=-c%20search_path%3Ddagster" in s.dsn


def test_admin_credentials_do_not_inherit_the_target_schema() -> None:
    """It has to create it; a search_path naming it would not resolve."""
    s = storage.Settings(host="pg", schema="dagster")
    admin = storage.admin_settings(s, {storage.ENV_ADMIN_USER: "postgres"})

    assert admin.schema == "public"
    assert admin.user == "postgres"
    assert admin.db == s.db and admin.host == s.host


def test_the_stack_home_is_rendered_from_the_tracked_base(tmp_path: Path) -> None:
    """Not copied once: the pool limits stay tracked to the file that has them."""
    base_dir = tmp_path / ".dagster"
    base_dir.mkdir()
    base = base_dir / "dagster.yaml"
    base.write_text(BASE_YAML)

    home = tmp_path / ".dagster-stack"
    path, changed = storage.write(home, storage.Settings(host="pg"), base=base)

    assert changed and path.parent == home
    assert "default_limit: 1" in path.read_text()
    assert "search_path=dagster" in path.read_text()
    # The tracked file is left exactly as it was.
    assert base.read_text() == BASE_YAML


# --------------------------------------------------------------- frontdoor --
def test_openmetadatas_api_outranks_recces_regardless_of_order(
        tmp_path: Path) -> None:
    """`^~` is what holds two apps that both own `/api` apart."""
    svcs = frontdoor.services(roster(tmp_path, ("acme", "acme-eu")))
    conf = frontdoor.nginx_conf(svcs)

    assert "location ^~ /api/v1/ {" in conf
    assert "location ^~ /api/ {" in conf


def test_recce_is_reached_by_cookie_not_by_prefix(tmp_path: Path) -> None:
    """A prefix would 404 in the SPA; see the module docstring."""
    svcs = frontdoor.services(roster(tmp_path, ("acme", "acme-eu"),
                                     ("zenith", "zenith-uk")))
    conf = frontdoor.nginx_conf(svcs)

    assert "map $cookie_pf_recce $pf_recce {" in conf
    assert '"zenith-uk" 127.0.0.1:8101;' in conf
    assert 'Set-Cookie "pf_recce=$pf_project' in conf
    assert "return 302 /lineage;" in conf


def test_every_recce_page_is_served_and_none_of_them_is_gzipped(
        tmp_path: Path) -> None:
    """sub_filter cannot substitute inside a gzipped response."""
    svcs = frontdoor.services(roster(tmp_path, ("acme", "acme-eu")))
    conf = frontdoor.nginx_conf(svcs)

    for route in frontdoor.RECCE_PAGES + frontdoor.RECCE_ASSETS:
        assert f"location ^~ {route} {{" in conf
    assert conf.count('proxy_set_header Accept-Encoding "";') == (
        len(frontdoor.RECCE_PAGES) + 1)  # + OpenMetadata's own


def test_the_proxied_host_header_keeps_its_port(tmp_path: Path) -> None:
    """`$host` drops it, and recce's own redirects then lose the front door."""
    svcs = frontdoor.services(roster(tmp_path, ("acme", "acme-eu")))
    conf = frontdoor.nginx_conf(svcs)

    assert "proxy_set_header Host $host;" not in conf
    assert "proxy_set_header Host $http_host;" in conf


def test_a_roster_with_no_dbt_project_renders_a_usable_front_door(
        tmp_path: Path) -> None:
    """The recce blocks reference a map that would not exist."""
    conf = frontdoor.nginx_conf([])

    assert "$pf_recce" not in conf
    assert "location / {" in conf
    assert f"location {frontdoor.DAGSTER_PREFIX}/ {{" in conf


def test_only_projects_with_a_review_start_on_boot(tmp_path: Path) -> None:
    """~350 MB each; eight of them for one review is how it ran out of memory."""
    r = roster(tmp_path, ("acme", "acme-eu"), ("jaffle", "jaffle-shop"))
    (r[1][2] / "transform" / "recce_state.json").write_text("{}")

    svcs = frontdoor.services(r)
    assert [s.reviewed for s in svcs] == [False, True]

    conf = frontdoor.supervisor_conf(svcs, [], repo=tmp_path,
                                     nginx_conf_path="/x/nginx.conf")
    acme = conf.split("[program:recce-acme-eu]")[1].split("[program:")[0]
    jaffle = conf.split("[program:recce-jaffle-shop]")[1].split("[program:")[0]
    assert "autostart=false" in acme
    assert "autostart=true" in jaffle


def test_code_servers_are_shared_not_forked_per_consumer(tmp_path: Path) -> None:
    """python_module entries would give the webserver and daemon one each."""
    locs = frontdoor.code_locations(roster(tmp_path, ("acme", "acme-eu"),
                                           ("zenith", "zenith-uk")))
    assert [x.port for x in locs] == [4000, 4001]

    ws = frontdoor.workspace_yaml(locs)
    assert ws.count("grpc_server:") == 2
    assert "- python_module:" not in ws  # the directive; the comment names it
    assert "location_name: zenith__zenith-uk" in ws


def test_a_project_without_definitions_gets_no_code_server(tmp_path: Path) -> None:
    """It would be a process supervisord restarts forever."""
    r = roster(tmp_path, ("acme", "acme-eu"), defs=False)
    assert frontdoor.code_locations(r) == []


def test_supervisor_pins_path_and_calls_the_venv_directly(tmp_path: Path) -> None:
    """`uv run` stays alive as a parent; dbt is resolved off PATH by dagster."""
    r = roster(tmp_path, ("acme", "acme-eu"))
    conf = frontdoor.supervisor_conf(frontdoor.services(r),
                                     frontdoor.code_locations(r),
                                     repo=tmp_path,
                                     nginx_conf_path="/x/nginx.conf")

    assert "uv run" not in conf
    assert f'environment=PATH="{frontdoor.VENV_BIN}:%(ENV_PATH)s"' in conf
    # supervisord resolves the command before it applies `directory`.
    assert "command=/opt/openmetadata/bin/openmetadata-server-start.sh" in conf


def test_the_webserver_is_told_the_prefix_nginx_does_not_strip(
        tmp_path: Path) -> None:
    conf = frontdoor.supervisor_conf([], [], repo=tmp_path,
                                     nginx_conf_path="/x/nginx.conf")
    assert f"--path-prefix {frontdoor.DAGSTER_PREFIX}" in conf


@pytest.mark.parametrize("html", ["landing", "down"])
def test_the_generated_pages_load_the_bar_as_same_origin_files(html: str) -> None:
    """OpenMetadata's CSP drops an inline script; a same-origin one passes."""
    page = (frontdoor.landing_html([]) if html == "landing"
            else frontdoor.recce_down_html())
    assert '/pf/bar.css' in page
    assert '<style>' in page or '/pf/bar.js' in page
