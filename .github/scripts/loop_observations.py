"""Loop observations become issues on the data-platform board.

The loops write what they see to `loop-ledger.json` and `STATE.md`. Both live
in the repository, which means an observation is only visible to someone who
goes looking. This script is the push half: after CI runs the loops, the
latest observation per (loop, project) is filed as an issue, updated in place
when it changes, and closed with a citation when a later run comes back clean.

Same conventions as `bot_findings.py`, deliberately — one board, one idiom:

  * a fingerprint in an HTML comment (`<!-- loop-observation:… -->`) makes the
    upsert idempotent; a re-run never files a duplicate;
  * a content hash on a second marker line means "changed" is detected by
    comparing markers, not by diffing prose;
  * closing cites the run that came back clean, so the issue history reads as
    observed → tracked → resolved;
  * the ProjectV2 board is optional: GITHUB_TOKEN files and closes issues, and
    only the board step needs PROJECTS_TOKEN (project scope). Without it the
    issues still land on the repository's issue list.

Labels: `loop-observation` (tracking) + `loop:<name>` per loop.

Run inside Actions (`loop-observations.yml`) or locally with `gh` logged in:

    python .github/scripts/loop_observations.py

Developing it needs neither gh nor a token:

    python .github/scripts/loop_observations.py --dry-run

reads the real ledger and prints exactly what would be filed, updated and
closed. Every gh/GraphQL call goes through `GH`/`bf.gql`, so the tests
(platform/tests/test_observations.py) inject fakes and assert on the calls;
`latest_observations(root)` takes the repo root, so a test feeds it a
temporary ledger rather than this repository's.
"""

from __future__ import annotations

import hashlib
import json
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import bot_findings as bf  # noqa: E402 — shared gh/gql helpers, same directory

ROOT = pathlib.Path(__file__).resolve().parents[2]
#: Every gh CLI call goes through this seam. Tests replace it; --dry-run
#: replaces it with a printer that answers reads with "nothing yet".
GH = bf.run
TRACKING_LABEL = "loop-observation"
MARK = "loop-observation:"
PROJECT_TITLE = os.environ.get("LOOP_PROJECT_TITLE") or "Platform observations"

#: Ladder validations are shipped as pull requests by `pf align ship`; filing
#: them here as well would say everything twice.
SKIP_PREFIX = "onboard-"


# ---------------------------------------------------------------- ledger ----
def latest_observations(root: pathlib.Path | None = None) -> list[dict]:
    """Newest ledger row per (loop, project), oldest first for stable output."""
    ledger = (ROOT if root is None else root) / "loop-ledger.json"
    if not ledger.exists():
        print("no loop-ledger.json — run `pf loop run-all` first")
        return []
    rows = json.loads(ledger.read_text(encoding="utf-8"))
    latest: dict[tuple[str, str], dict] = {}
    for e in rows:
        loop = e.get("loop", "")
        if loop.startswith(SKIP_PREFIX) or e.get("outcome") == "circuit_open":
            continue
        latest[(loop, e.get("project", ""))] = e
    return [latest[k] for k in sorted(latest)]


def fingerprint(e: dict) -> str:
    return f"{e['loop']}@{e.get('group', '')}/{e['project']}"


def content_hash(e: dict) -> str:
    blob = json.dumps({"findings": e.get("findings"), "proposals": [
        p.get("status") for p in e.get("proposals") or []]}, sort_keys=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:12]


# ---------------------------------------------------------------- issues ----
def tracked() -> dict[str, dict]:
    out = GH(["gh", "issue", "list", "--repo", bf.REPO, "--label", TRACKING_LABEL,
                  "--state", "all", "--limit", "500",
                  "--json", "number,title,state,body"], check=False)
    index: dict[str, dict] = {}
    for issue in json.loads(out or "[]"):
        for line in (issue.get("body") or "").splitlines():
            if MARK in line:
                fp = line.split(MARK, 1)[1].split("-->", 1)[0].strip().split()[0]
                # Newest issue wins a fingerprint; older ones were closed.
                if fp not in index or issue["number"] > index[fp]["number"]:
                    index[fp] = issue
    print(f"index: {len(index)} tracked observation(s)")
    return index


def render(e: dict) -> tuple[str, str]:
    findings = e.get("findings") or []
    title = (f"[loop] {e['loop']} · {e.get('group', '?')}/{e['project']}: "
             f"{findings[0][:80] if findings else 'observation'}")
    lines = [f"<!-- {MARK}{fingerprint(e)} -->",
             f"<!-- {MARK}hash:{content_hash(e)} -->", "",
             f"**Loop:** `{e['loop']}` · **Project:** `{e.get('group', '?')}/"
             f"{e['project']}` · **Level:** {e.get('level') or 'L1'} · "
             f"**Run:** `{e.get('run_id')}` at {e.get('started_at')}", "",
             "### Observations", ""]
    lines += [f"- {f}" for f in findings] or ["- (none)"]
    if e.get("suppressed"):
        lines += ["", f"_{len(e['suppressed'])} finding(s) suppressed by "
                      f"`decisions/loop-memory.yaml` — `pf loop memory list` shows why._"]
    for p in e.get("proposals") or []:
        where = p.get("pr_url") or p.get("branch") or p.get("path") or ""
        lines += ["", f"↗ proposal `{p.get('proposal_id')}` **{p.get('status')}** {where}"]
    lines += ["", "---",
              "Filed by the loop-observations workflow from `loop-ledger.json`. "
              "It updates in place when the observation changes and closes itself "
              "on the next clean run. Suppress a known condition with "
              "`pf loop memory add` — with a reason and an expiry — rather than "
              "closing this by hand."]
    return title, "\n".join(lines)


def ensure_labels(loops: set[str]) -> None:
    GH(["gh", "label", "create", TRACKING_LABEL, "--repo", bf.REPO,
        "--color", "D93F0B", "--description",
        "An observation a platform loop is currently making", "--force"], check=False)
    for loop in sorted(loops):
        GH(["gh", "label", "create", f"loop:{loop}", "--repo", bf.REPO,
            "--color", "0E8A16", "--force"], check=False)


def upsert(e: dict, index: dict[str, dict], board) -> None:
    fp = fingerprint(e)
    title, body = render(e)
    have = index.get(fp)
    if have and have["state"] == "OPEN":
        if f"hash:{content_hash(e)}" in (have.get("body") or ""):
            print(f"  unchanged  #{have['number']}  {fp}")
            return
        GH(["gh", "issue", "edit", str(have["number"]), "--repo", bf.REPO,
            "--title", title, "--body", body], check=False)
        GH(["gh", "issue", "comment", str(have["number"]), "--repo", bf.REPO,
            "--body", f"Observation changed on run `{e.get('run_id')}` "
                      f"({e.get('started_at')}); body updated in place."], check=False)
        print(f"  updated    #{have['number']}  {fp}")
        return
    out = GH(["gh", "issue", "create", "--repo", bf.REPO, "--title", title,
              "--body", body, "--label", TRACKING_LABEL,
              "--label", f"loop:{e['loop']}"], check=False)
    number = int(out.rstrip("/").rsplit("/", 1)[-1]) if out.strip() else 0
    print(f"  filed      #{number or '?'}  {fp}")
    add_to_board(board, number)


def close_clean(e: dict, index: dict[str, dict]) -> None:
    have = index.get(fingerprint(e))
    if not have or have["state"] != "OPEN":
        return
    GH(["gh", "issue", "comment", str(have["number"]), "--repo", bf.REPO,
        "--body", f"Closed automatically: run `{e.get('run_id')}` at "
                  f"{e.get('started_at')} came back clean — the loop no longer "
                  f"observes this. Reopen if it should not have cleared."], check=False)
    GH(["gh", "issue", "close", str(have["number"]), "--repo", bf.REPO,
        "--reason", "completed"], check=False)
    print(f"  closed     #{have['number']}  {fingerprint(e)}")


# ----------------------------------------------------------------- board ----
def ensure_board():
    """The observations ProjectV2, created and linked on first use. Optional."""
    if not bf.PROJECT_TOKEN:
        print("::warning::PROJECTS_TOKEN not set — issues tracked, board skipped")
        return None
    nodes = bf.gql('query($l:String!){organization(login:$l){projectsV2(first:100)'
                   '{nodes{id title number}}}}', bf.PROJECT_TOKEN,
                   l=bf.OWNER)["data"]["organization"]["projectsV2"]["nodes"]
    proj = next((p for p in nodes if p["title"] == PROJECT_TITLE), None)
    if not proj:
        oid = bf.gql('query($l:String!){organization(login:$l){id}}',
                     bf.PROJECT_TOKEN, l=bf.OWNER)["data"]["organization"]["id"]
        proj = bf.gql('mutation($o:ID!,$t:String!){createProjectV2(input:{ownerId:$o,'
                      'title:$t}){projectV2{id title number}}}', bf.PROJECT_TOKEN,
                      o=oid, t=PROJECT_TITLE)["data"]["createProjectV2"]["projectV2"]
        rid = bf.gql('query($o:String!,$r:String!){repository(owner:$o,name:$r){id}}',
                     bf.PROJECT_TOKEN, o=bf.OWNER, r=bf.NAME)["data"]["repository"]["id"]
        bf.gql('mutation($p:ID!,$r:ID!){linkProjectV2ToRepository(input:{projectId:$p,'
               'repositoryId:$r}){repository{id}}}', bf.PROJECT_TOKEN,
               p=proj["id"], r=rid)
        print(f"created project #{proj['number']} '{PROJECT_TITLE}' and linked it")
    return proj["id"]


def add_to_board(board, issue_no: int) -> None:
    if not board or not issue_no:
        return
    nid = bf.gql('query($o:String!,$r:String!,$n:Int!){repository(owner:$o,name:$r)'
                 '{issue(number:$n){id}}}', bf.PROJECT_TOKEN, o=bf.OWNER, r=bf.NAME,
                 n=issue_no)["data"]["repository"]["issue"]["id"]
    bf.gql('mutation($p:ID!,$c:ID!){addProjectV2ItemById(input:{projectId:$p,'
           'contentId:$c}){item{id}}}', bf.PROJECT_TOKEN, p=board, c=nid)
    print("    board: added")


# ------------------------------------------------------------------ main ----
def _dry_gh(cmd: list[str], token=None, check: bool = True) -> str:
    """Reads answer empty; writes print themselves. The whole plan, no GitHub."""
    verb = cmd[1:3]
    if verb == ["issue", "list"]:
        return "[]"
    print(f"  DRY {' '.join(cmd[:4])}" + (f"  {cmd[cmd.index('--title') + 1]!r}"
                                          if "--title" in cmd else ""))
    return ""


def main(argv: list[str] | None = None) -> None:
    global GH
    args = argv if argv is not None else sys.argv[1:]
    dry = "--dry-run" in args
    if dry:
        GH = _dry_gh
        bf.REPO = bf.REPO or "local/dry-run"
        bf.PROJECT_TOKEN = ""
    if not bf.REPO:
        sys.exit("GITHUB_REPOSITORY is not set")
    obs = latest_observations()
    if not obs:
        return
    with_findings = [e for e in obs if e.get("findings") or e.get("proposals")]
    clean = [e for e in obs if not e.get("findings") and not e.get("proposals")]
    print(f"{len(obs)} observation(s): {len(with_findings)} active, {len(clean)} clean"
          + ("  [dry-run]" if dry else ""))

    ensure_labels({e["loop"] for e in with_findings})
    index = tracked()
    board = ensure_board()
    for e in with_findings:
        upsert(e, index, board)
    for e in clean:
        close_clean(e, index)


if __name__ == "__main__":
    main()
