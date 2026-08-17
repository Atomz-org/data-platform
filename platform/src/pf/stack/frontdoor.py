"""One origin for three UIs, and the process table that serves them.

## The problem, stated exactly

OpenMetadata's UI and recce's UI are both *root-anchored* single-page apps. Both
fetch their bundles from `/`, and both call an API under `/api`. Serving recce
at `/recce/<project>/` the obvious way — a path-prefixed reverse proxy — does not
work: recce's frontend is a Next.js static export built with no `basePath`, so
its HTML asks for `/_next/...` no matter what path served it, and its client
router matches on `window.location.pathname` against routes that all start at
`/`. Landing on `/recce/acme-eu/` renders its 404. Rebuilding the bundle with a
basePath is the only clean fix and the bundle is vendored (`vendor/recce/ui`),
which this repository does not build.

So the merge happens on the *paths*, not on a prefix. The two apps turn out not
to overlap:

    /api/v1/...                 OpenMetadata's REST API. Its only API prefix.
    /api/...                    recce's REST API and websocket. Never versioned.
    /_next/, /lineage, /checks,
    /query, /logo/, /imgs/      recce, and nothing else on this origin.
    /dagster/...                Dagster, which supports --path-prefix natively.
    everything else             OpenMetadata.

`^~` makes `/api/v1/` beat `/api/` regardless of ordering, which is the one rule
holding the two APIs apart.

## Which project's recce

recce serves one project per process, so the shared root routes need a subject.
A cookie carries it: `/recce/<project>` sets `pf_recce` and redirects to
`/lineage`, and an nginx `map` turns that cookie into the port for that
project's server. One project is in view at a time, which matches what a review
*is* — you are reading one diff — and an unknown or absent cookie falls back to
the first project rather than a blank page.

The ports are assigned from the sorted roster, so they are stable for a fixed
set of projects and shift when one is added. That is fine because nothing
persists them: `pf stack render` regenerates nginx and supervisor together, and
they are only ever read by the container.

## Why the bar is a script tag and not inline HTML

The injected "which app am I in" bar loads `/pf/bar.css` and `/pf/bar.js` rather
than carrying its own `<style>`. OpenMetadata sends a Content-Security-Policy;
an inline style or an inline script is dropped under `'self'`, and the bar would
silently not appear on exactly one of the two apps. Same-origin files pass.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

#: First recce port. Above the ephemeral range Dagster and OpenMetadata use and
#: below 8585, so a `lsof` on a broken stack reads in service order.
RECCE_PORT_BASE = 8100

#: First Dagster code-server port. See `code_locations` for why they are
#: standalone processes rather than children of the webserver.
CODE_PORT_BASE = 4000

LISTEN = 8080
OM_ADDR = "127.0.0.1:8585"
DAGSTER_ADDR = "127.0.0.1:3000"
DAGSTER_PREFIX = "/dagster"
#: What `Definitions` names the repository inside a code location. Dagster's own
#: URLs are `<repo>@<location>`, so the launcher has to spell it out.
DAGSTER_REPO = "__repository__"

#: Root paths that belong to recce's static export. Derived from the wheel's
#: `recce/data/` directory; if a recce upgrade adds a route it must be added
#: here, or that route will be answered by OpenMetadata's SPA instead.
#:
#: Split because only the HTML routes get the injected bar, and injection means
#: `Accept-Encoding: ""` — asking recce for the megabyte of `/_next/` chunks
#: uncompressed on every page load, to substitute a string that is not in them.
RECCE_PAGES = ("/lineage", "/checks", "/query", "/_not-found", "/404")
RECCE_ASSETS = ("/_next/", "/logo/", "/imgs/")


@dataclass(frozen=True)
class Recce:
    """One project's review server."""

    group: str
    project: str
    port: int
    project_dir: Path
    #: False when the project has no recorded review. The server is still
    #: started — recce serves a live single-environment session — but the
    #: landing page says so, because "no diff" and "no baseline" look identical
    #: in the UI and mean opposite things.
    reviewed: bool = True

    @property
    def location(self) -> str:
        return f"/recce/{self.project}"


def services(roster: list[tuple[str, str, Path]], *,
             base: int = RECCE_PORT_BASE) -> list[Recce]:
    """Assign a port to every project that has a dbt project to review.

    A project with no `transform/dbt_project.yml` is skipped rather than given a
    server that would exit immediately — a supervisor restarting a doomed
    process forever is noise that hides the ones that are genuinely failing.
    """
    from pf.tools import recce as recce_tool

    out: list[Recce] = []
    for group, project, project_dir in roster:
        if not (recce_tool.dbt_dir(project_dir) / "dbt_project.yml").exists():
            continue
        out.append(Recce(
            group=group,
            project=project,
            port=base + len(out),
            project_dir=project_dir,
            reviewed=recce_tool.state_file(project_dir).exists(),
        ))
    return out


@dataclass(frozen=True)
class CodeLocation:
    """One project's Dagster code server."""

    group: str
    project: str
    module: str
    port: int
    working_dir: Path

    @property
    def name(self) -> str:
        return f"{self.group}__{self.project}"


def code_locations(roster: list[tuple[str, str, Path]], *,
                   base: int = CODE_PORT_BASE) -> list[CodeLocation]:
    """One long-lived gRPC server per project, shared by webserver and daemon.

    This is the difference between the stack fitting in memory and not. A
    `python_module` entry in workspace.yaml is not a shared service: the
    webserver spawns its own child gRPC process per location, and the daemon
    spawns a *second* one, so eight projects became nineteen Python processes
    holding 3.1 GB — enough, on an 8 GB machine, to squeeze Elasticsearch until
    it refused connections and Postgres until it dropped OpenMetadata's.

    A `grpc_server` entry points both at the same process. Eight servers,
    ~1.4 GB, and reloading one project no longer restarts the other seven.
    """
    out: list[CodeLocation] = []
    for group, project, project_dir in roster:
        module = project.replace("-", "_")
        src = project_dir / "src"
        if not (src / module / "definitions.py").exists():
            continue
        out.append(CodeLocation(group=group, project=project, module=module,
                                port=base + len(out), working_dir=src))
    return out


def workspace_yaml(locations: list[CodeLocation], *,
                   host: str = "127.0.0.1") -> str:
    """A workspace of gRPC servers, for the stack.

    Written beside `platform/workspace.yaml` rather than over it. That file
    loads code in-process and is what `dagster dev` on a laptop needs; this one
    is useless without the servers supervisord starts, and swapping them would
    make host development fail with "connection refused" against ports nobody
    is listening on.
    """
    lines = [
        "# GENERATED by `pf stack render`. For the containerised stack only.",
        "#",
        "# grpc_server, not python_module: the webserver and the daemon connect",
        "# to one process per project instead of forking one each. See",
        "# pf/stack/frontdoor.py:code_locations.",
        "load_from:",
    ]
    for loc in locations:
        lines += [
            "  - grpc_server:",
            f"      host: {host}",
            f"      port: {loc.port}",
            f"      location_name: {loc.name}",
        ]
    return "\n".join(lines) + "\n"


# ------------------------------------------------------------------ nginx --
def _inject(app: str, project: str = "") -> list[str]:
    """The sub_filter that puts the navigation bar on a proxied HTML page.

    `Accept-Encoding: ""` goes with it and is not optional — nginx cannot
    substitute inside a gzipped response, and without it the filter matches
    nothing and fails silently.
    """
    data = f' data-project={project}' if project else ""
    tag = ('<link rel="stylesheet" href="/pf/bar.css">'
           f'<script src="/pf/bar.js" data-app="{app}"{data} defer></script>')
    return [
        '            proxy_set_header Accept-Encoding "";',
        f"            sub_filter '</body>' '{tag}</body>';",
        "            sub_filter_once on;",
    ]


def _map_block(name: str, values: dict[str, str], default: str) -> list[str]:
    lines = [f"    map $cookie_pf_recce {name} {{",
             f"        default {default};"]
    lines += [f'        "{k}" {v};' for k, v in values.items()]
    lines.append("    }")
    return lines


def nginx_conf(svcs: list[Recce], *, listen: int = LISTEN, om: str = OM_ADDR,
               dagster: str = DAGSTER_ADDR, static: str = "/opt/pf/www") -> str:
    """A complete nginx configuration — main context included.

    Complete rather than a snippet dropped in `conf.d` because the `map`
    directives belong to `http{}`, and a generated file that only works when
    something else includes it in the right context is a file that fails at
    3 a.m. Run it with `nginx -c <this file>`.
    """
    lines = [
        "# GENERATED by `pf stack render`. Re-run after adding a project.",
        "#",
        "# One origin, three apps. See pf/stack/frontdoor.py for why recce is",
        "# routed by path and cookie rather than mounted under a prefix.",
        "",
        "worker_processes auto;",
        "error_log /dev/stderr warn;",
        "pid /run/nginx-pf.pid;",
        "daemon off;",
        "",
        "events { worker_connections 1024; }",
        "",
        "http {",
        "    include /etc/nginx/mime.types;",
        "    default_type application/octet-stream;",
        "    access_log /dev/stdout;",
        "    sendfile on;",
        "    server_tokens off;",
        "",
        "    # OpenMetadata accepts glossary and ingestion payloads well past the",
        "    # 1m default, and a truncated PUT surfaces as a schema error.",
        "    client_max_body_size 64m;",
        "    proxy_read_timeout 300s;",
        "    proxy_send_timeout 300s;",
        "",
        "    # All three apps hold websockets open: recce's /api/ws, Dagster's",
        "    # GraphQL subscriptions, OpenMetadata's activity feed.",
        "    map $http_upgrade $connection_upgrade {",
        "        default upgrade;",
        "        ''      close;",
        "    }",
        "",
    ]

    if svcs:
        ports = {s.project: f"127.0.0.1:{s.port}" for s in svcs}
        labels = {s.project: f'"{s.project}"' for s in svcs}
        first = svcs[0]
        lines += [
            "    # Which project's review the shared recce routes belong to.",
            "    # An unset or unknown cookie falls back to the first project so",
            "    # that a bare visit renders something rather than a 502.",
        ]
        lines += _map_block("$pf_recce", ports, f"127.0.0.1:{first.port}")
        lines.append("")
        lines += _map_block("$pf_recce_name", labels, f'"{first.project}"')
        lines.append("")

    lines += [
        "    upstream pf_openmetadata { server " + om + "; }",
        "    upstream pf_dagster      { server " + dagster + "; }",
        "",
        "    server {",
        f"        listen {listen};",
        f"        listen [::]:{listen};",
        "        server_name _;",
        "",
        "        # ---- the launcher ------------------------------------------",
        "        location = /pf { return 302 /pf/; }",
        "        location /pf/ {",
        f"            alias {static}/;",
        "            index index.html;",
        "        }",
        "",
        "        # ---- Dagster -----------------------------------------------",
        f"        # dagster-webserver runs with --path-prefix {DAGSTER_PREFIX}, so",
        "        # the prefix is passed through rather than stripped.",
        f"        location = {DAGSTER_PREFIX} {{ return 302 {DAGSTER_PREFIX}/; }}",
        f"        location {DAGSTER_PREFIX}/ {{",
        "            proxy_pass http://pf_dagster;",
        "            proxy_http_version 1.1;",
        "            proxy_set_header Upgrade $http_upgrade;",
        "            proxy_set_header Connection $connection_upgrade;",
        "            proxy_set_header Host $http_host;",
        "            proxy_set_header X-Forwarded-Proto $scheme;",
        "        }",
        "",
    ]

    if svcs:
        lines += [
            "        # ---- recce -------------------------------------------------",
            "        # The entry point: name the project, then hand the browser a",
            "        # real recce route. Redirecting rather than proxying is what",
            "        # keeps the SPA's router and its /_next/ requests agreeing.",
            "        location ~ ^/recce/(?<pf_project>[A-Za-z0-9_.-]+)/?$ {",
            '            add_header Set-Cookie "pf_recce=$pf_project; Path=/; SameSite=Lax" always;',
            "            return 302 /lineage;",
            "        }",
            "",
            "        location ^~ /api/v1/ {",
            "            # OpenMetadata's only API prefix. `^~` wins over /api/",
            "            # below no matter how the blocks are ordered.",
            "            proxy_pass http://pf_openmetadata;",
            "            proxy_http_version 1.1;",
            "            proxy_set_header Upgrade $http_upgrade;",
            "            proxy_set_header Connection $connection_upgrade;",
            "            proxy_set_header Host $http_host;",
            "            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;",
            "            proxy_set_header X-Forwarded-Proto $scheme;",
            "        }",
            "",
            "        location ^~ /api/ {",
            "            proxy_pass http://$pf_recce;",
            "            proxy_http_version 1.1;",
            "            proxy_set_header Upgrade $http_upgrade;",
            "            proxy_set_header Connection $connection_upgrade;",
            "            proxy_set_header Host $http_host;",
            "        }",
            "",
        ]
        # Most review servers are not autostarted (see supervisor_conf), so a
        # refused connection is the normal case, not a fault. Say which project
        # and how to start it instead of nginx's bare 502.
        down = [
            "            proxy_intercept_errors on;",
            "            error_page 502 503 504 = @recce_down;",
        ]
        for route in RECCE_ASSETS:
            lines += [
                f"        location ^~ {route} {{",
                "            proxy_pass http://$pf_recce;",
                "            proxy_set_header Host $http_host;",
                *down,
                "        }",
                "",
            ]
        for route in RECCE_PAGES:
            lines += [
                f"        location ^~ {route} {{",
                "            proxy_pass http://$pf_recce;",
                "            proxy_set_header Host $http_host;",
                *down,
                *_inject("recce", "$pf_recce_name"),
                "        }",
                "",
            ]
        lines += [
            "        location @recce_down {",
            f"            root {static};",
            "            add_header Cache-Control \"no-store\" always;",
            "            try_files /recce-down.html =503;",
            "        }",
            "",
        ]

    lines += [
        "        # ---- OpenMetadata, and anything unclaimed -------------------",
        "        location / {",
        "            proxy_pass http://pf_openmetadata;",
        "            proxy_http_version 1.1;",
        "            proxy_set_header Upgrade $http_upgrade;",
        "            proxy_set_header Connection $connection_upgrade;",
        "            proxy_set_header Host $http_host;",
        "            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;",
        "            proxy_set_header X-Forwarded-Proto $scheme;",
        *_inject("catalog"),
        "        }",
        "    }",
        "}",
    ]
    return "\n".join(lines) + "\n"


# ------------------------------------------------------------- supervisor --
#: Where the container's virtualenv lives. Supervisor calls these binaries
#: directly rather than going through `uv run`: `uv run` re-resolves the project
#: and then execs, so it stays alive as a parent for the whole life of the
#: process — 40 MB × every program, for nothing, since the entrypoint has
#: already synced and PATH already points here.
VENV_BIN = "/opt/venv/bin"


def supervisor_conf(svcs: list[Recce], locations: list[CodeLocation], *,
                    repo: Path, nginx_conf_path: str,
                    om_home: str = "/opt/openmetadata",
                    workspace: str = "platform/stack/workspace.yaml",
                    bin_dir: str = VENV_BIN,
                    dagster_port: int = 3000) -> str:
    """The process table for the single-image stack.

    Priorities, not `depends_on`: supervisord has no readiness model, so the
    order below is a nudge and every consumer has to tolerate its dependency
    being slow. nginx starting before OpenMetadata is fine — it answers 502 for
    a few seconds. dagster-webserver starting before Postgres accepts
    connections is not fine, which is why the entrypoint blocks on the database
    *before* supervisord is exec'd rather than racing it here.
    """
    def program(name: str, command: str, *, directory: str, priority: int,
                autostart: bool = True,
                extra: list[str] | None = None) -> list[str]:
        return [
            f"[program:{name}]",
            f"command={command}",
            f"directory={directory}",
            f"priority={priority}",
            f"autostart={'true' if autostart else 'false'}",
            "autorestart=true",
            "startretries=3",
            "stopasgroup=true",
            "killasgroup=true",
            "stdout_logfile=/dev/fd/1",
            "stdout_logfile_maxbytes=0",
            "redirect_stderr=true",
            # Pinned, not inherited. Dagster's dbt resource resolves the `dbt`
            # executable off PATH at *resource construction*, so a program whose
            # PATH lost the venv fails with "the dbt executable does not exist"
            # — a message about dbt for a problem in the process manager.
            f'environment=PATH="{bin_dir}:%(ENV_PATH)s"',
            *(extra or []),
            "",
        ]

    lines = [
        "; GENERATED by `pf stack render`. Re-run after adding a project.",
        "",
        "[supervisord]",
        "nodaemon=true",
        "logfile=/dev/null",
        "logfile_maxbytes=0",
        "pidfile=/run/supervisord.pid",
        "",
        "[unix_http_server]",
        "file=/run/supervisor.sock",
        "",
        "[rpcinterface:supervisor]",
        ("supervisor.rpcinterface_factory = "
         "supervisor.rpcinterface:make_main_rpcinterface"),
        "",
        "[supervisorctl]",
        "serverurl=unix:///run/supervisor.sock",
        "",
    ]

    # Absolute command, relative argument. supervisord resolves the *command*
    # against PATH before it applies `directory`, so the `./bin/...` spelling
    # OpenMetadata's own start script uses fails with "can't find command" while
    # the config it is passed still has to resolve against the distribution
    # root.
    lines += program(
        "openmetadata",
        f"{om_home}/bin/openmetadata-server-start.sh conf/openmetadata.yaml",
        directory=om_home, priority=10)

    # Before the webserver and the daemon, which connect to them.
    for loc in locations:
        lines += program(
            f"code-{loc.project}",
            f"{bin_dir}/dagster code-server start -h 127.0.0.1 -p {loc.port} "
            f"-m {loc.module}.definitions -d {loc.working_dir} "
            f"--location-name {loc.name} --max-workers 2",
            directory=str(loc.working_dir), priority=15)

    # 0.0.0.0, unlike everything else here. The compose file publishes
    # 127.0.0.1:3000 so `dagster` CLI clients on the host can reach the
    # webserver directly, and a container-loopback bind makes that publish a
    # dead port: podman forwards to the container's external interface, nothing
    # is listening there, and the host gets connection refused for a process
    # that is running perfectly. Loopback-only exposure is the *host* side's
    # job, and it is already doing it.
    lines += program(
        "dagster-webserver",
        f"{bin_dir}/dagster-webserver -w {workspace} -h 0.0.0.0 "
        f"-p {dagster_port} --path-prefix {DAGSTER_PREFIX}",
        directory=str(repo), priority=20)

    lines += program(
        "dagster-daemon",
        f"{bin_dir}/dagster-daemon run -w {workspace}",
        directory=str(repo), priority=21)

    for s in svcs:
        # `pf tool recce serve` rather than `recce server` directly: it is what
        # sets PF_DUCKDB_PATH and picks review mode when a state file exists,
        # and duplicating that here would let the container and the CLI show
        # different numbers for the same project.
        #
        # autostart only where there is a review to serve. A recce process is
        # ~150 MB of dbt manifest whether or not it has anything to show, and
        # eight of them for one review is how the stack ran out of memory. The
        # rest stay in the process table, one `supervisorctl start` away, and
        # the front door says so when their port does not answer.
        lines += program(
            f"recce-{s.project}",
            f"{bin_dir}/pf tool recce serve {s.group} {s.project} "
            f"--port {s.port} --host 127.0.0.1",
            directory=str(repo), priority=30, autostart=s.reviewed)

    lines += program("nginx", f"nginx -c {nginx_conf_path}",
                     directory="/", priority=40)
    return "\n".join(lines)


# ------------------------------------------------------------------- www --
def landing_html(svcs: list[Recce], *, listen: int = LISTEN) -> str:
    """The `/pf/` launcher: every project, and the three things you can open."""
    rows = []
    for s in svcs:
        service = f"{s.group}_{s.project}".replace("-", "_")
        review = ("review" if s.reviewed
                  else "<span class='muted'>no recorded review</span>")
        # Dagster addresses a code location as `<repo>@<location>`, and
        # `Definitions` always yields the repository name `__repository__`. The
        # bare `/locations/<location>/…` spelling looks right, renders, and
        # resolves to nothing.
        at = f"{DAGSTER_REPO}@{s.group}__{s.project}"
        job = f"{s.project.replace('-', '_')}_catalog_sync"
        rows.append(f"""      <tr>
        <td><strong>{s.project}</strong><div class="muted">{s.group}</div></td>
        <td><a href="/databaseService/{service}">catalogue</a></td>
        <td><a href="{DAGSTER_PREFIX}/locations/{at}/asset-groups">assets</a></td>
        <td><a href="{s.location}">{review}</a></td>
        <td><a href="{DAGSTER_PREFIX}/locations/{at}/jobs/{job}">catalog sync</a></td>
      </tr>""")

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Platform control plane</title>
<link rel="stylesheet" href="/pf/bar.css">
<style>
  body {{ font: 15px/1.5 ui-sans-serif, system-ui, sans-serif; margin: 0;
         background: #0f1117; color: #e6e8ee; }}
  main {{ max-width: 60rem; margin: 0 auto; padding: 3rem 1.5rem 6rem; }}
  h1 {{ font-size: 1.5rem; margin: 0 0 .25rem; }}
  p.lede {{ color: #9aa3b8; margin: 0 0 2rem; }}
  table {{ width: 100%; border-collapse: collapse; }}
  th, td {{ text-align: left; padding: .7rem .6rem;
            border-bottom: 1px solid #232838; vertical-align: top; }}
  th {{ font-size: .75rem; text-transform: uppercase; letter-spacing: .06em;
        color: #7b849b; font-weight: 600; }}
  a {{ color: #7aa2f7; text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}
  .muted {{ color: #6b7386; font-size: .8rem; }}
  nav a {{ display: inline-block; margin-right: 1.2rem; }}
</style>
</head>
<body>
<main>
  <h1>Platform control plane</h1>
  <p class="lede">One origin, port {listen}: the catalogue at
     <code>/</code>, orchestration at <code>{DAGSTER_PREFIX}/</code>, and one
     recce review per project.</p>
  <nav><a href="/">Catalogue</a><a href="{DAGSTER_PREFIX}/">Dagster</a></nav>
  <table>
    <thead><tr><th>project</th><th>catalogue</th><th>assets</th>
      <th>recce</th><th>refresh</th></tr></thead>
    <tbody>
{chr(10).join(rows) if rows else
 '      <tr><td colspan="5" class="muted">No project has a dbt project yet.</td></tr>'}
    </tbody>
  </table>
</main>
</body>
</html>
"""


def recce_down_html() -> str:
    """Served when a review server's port does not answer.

    Which is expected: only projects with a recorded review are autostarted.
    A page that explains that is the difference between "the stack is broken"
    and "this one is asleep".
    """
    return """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Review server not running</title>
<link rel="stylesheet" href="/pf/bar.css">
<style>
  body { font: 15px/1.6 ui-sans-serif, system-ui, sans-serif; margin: 0;
         background: #0f1117; color: #e6e8ee;
         display: grid; place-items: center; min-height: 100vh; }
  main { max-width: 34rem; padding: 2rem; }
  h1 { font-size: 1.2rem; margin: 0 0 .75rem; }
  p { color: #9aa3b8; }
  code { background: #1a1e2b; padding: .15rem .4rem; border-radius: 4px;
         font-size: .85em; color: #cbd3e6; }
  pre { background: #1a1e2b; padding: .8rem 1rem; border-radius: 8px;
        overflow-x: auto; color: #cbd3e6; }
  a { color: #7aa2f7; }
</style>
</head>
<body>
<main>
  <h1>This project's review server is not running.</h1>
  <p>Only projects with a recorded review start automatically — the rest stay
     stopped so eight idle servers do not hold a gigabyte between them.</p>
  <p>Start it:</p>
  <pre>podman exec pf_stack supervisorctl \\
  -c "$PF_REPO/platform/stack/supervisord.conf" \\
  start recce-&lt;project&gt;</pre>
  <p>Or record a review first, which is usually what is actually missing:
     <code>pf tool recce run &lt;group&gt; &lt;project&gt;</code></p>
  <p><a href="/pf/">Back to the launcher</a></p>
</main>
<script src="/pf/bar.js" data-app="recce" defer></script>
</body>
</html>
"""


def bar_css() -> str:
    return """/* GENERATED by `pf stack render`. */
#pf-bar {
  position: fixed; z-index: 2147483000; bottom: 14px; left: 14px;
  display: flex; align-items: center; gap: 10px;
  padding: 6px 12px; border-radius: 999px;
  background: rgba(15, 17, 23, .92); color: #e6e8ee;
  border: 1px solid rgba(255, 255, 255, .12);
  box-shadow: 0 6px 20px rgba(0, 0, 0, .35);
  font: 12px/1 ui-sans-serif, system-ui, sans-serif;
}
#pf-bar a { color: #7aa2f7; text-decoration: none; }
#pf-bar a:hover { text-decoration: underline; }
#pf-bar .pf-here { color: #e6e8ee; font-weight: 600; }
#pf-bar .pf-sep { color: #3a4157; }
"""


def bar_js() -> str:
    """The bar, built in script so it survives a `'self'` CSP.

    Reads its own `<script>` tag's data attributes rather than sniffing the URL:
    nginx already decided which app answered this request, and re-deriving that
    in the browser would give two sources of truth that disagree on `/`.
    """
    return """// GENERATED by `pf stack render`.
(function () {
  var me = document.currentScript ||
           document.querySelector('script[src="/pf/bar.js"]');
  var app = (me && me.dataset.app) || "catalog";
  var project = (me && me.dataset.project) || "";

  function link(href, text) {
    var a = document.createElement("a");
    a.href = href; a.textContent = text; return a;
  }
  function sep() {
    var s = document.createElement("span");
    s.className = "pf-sep"; s.textContent = "\\u00b7"; return s;
  }

  function mount() {
    if (document.getElementById("pf-bar")) return;
    var bar = document.createElement("div");
    bar.id = "pf-bar";
    bar.appendChild(link("/pf/", "platform"));
    bar.appendChild(sep());

    if (app === "recce") {
      bar.appendChild(link("/", "catalogue"));
      bar.appendChild(sep());
      var here = document.createElement("span");
      here.className = "pf-here";
      here.textContent = "recce" + (project ? " \\u00b7 " + project : "");
      bar.appendChild(here);
    } else {
      var h = document.createElement("span");
      h.className = "pf-here"; h.textContent = "catalogue";
      bar.appendChild(h);
    }
    bar.appendChild(sep());
    bar.appendChild(link("/dagster/", "dagster"));
    document.body.appendChild(bar);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mount);
  } else {
    mount();
  }
})();
"""
