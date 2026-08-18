#!/usr/bin/env python3
"""Carry CodeRabbit and Gitar review findings into tracked issues on a board,
and close those issues again when the finding is actually fixed.

A review comment dies with its pull request: merge the PR and the finding is
archived behind a "resolved" fold nobody reopens. This turns each finding into
an issue that outlives the PR, files it on a project board under a priority and
category derived from what the bot itself said, and — once the review thread is
resolved — closes the issue citing the commit that fixed it.

Events it runs on (see .github/workflows/bot-findings.yml):

  pull_request_review_comment  a new inline finding, tracked as it lands
  issue_comment                a bot's summary comment, which may hold several
  workflow_run / pull_request  reconcile: every other pipeline has finished, so
                               re-read the PR, file what is new and close what
                               is fixed
  workflow_dispatch            backfill one PR, or every open one

Every issue carries a fingerprint of (path, normalised title). That fingerprint
is what makes this idempotent: re-running over the same PR updates the existing
issue instead of filing a second, the same defect reported by both bots
collapses into one issue with both citations, and a resolved thread can be
matched back to the issue it came from.

Writing to a ProjectV2 needs a token with `project` scope, which GITHUB_TOKEN
does not have. Set the PROJECTS_TOKEN secret to enable the board; without it
issues are still filed and closed, and only the board step is skipped.
"""

from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import time
from dataclasses import dataclass

BOTS = ("coderabbitai", "gitar-bot")

REPO = os.environ.get("GITHUB_REPOSITORY", "")
OWNER = REPO.split("/")[0] if REPO else ""
NAME = REPO.split("/")[1] if "/" in REPO else ""
PROJECT_TITLE = os.environ.get("PROJECT_TITLE") or "Bot findings — carried from PR review"
PROJECT_TOKEN = os.environ.get("PROJECTS_TOKEN") or ""

TRACKING_LABEL = "bot-finding"
MARK = "bot-finding:"

PRIORITIES = [("P0 — Critical", "RED"), ("P1 — High", "ORANGE"),
              ("P2 — Medium", "YELLOW"), ("P3 — Low", "GRAY")]
CATEGORIES = [("Security & Secrets", "RED"), ("Catalog & Metadata", "BLUE"),
              ("Toolkit Hooks & Scripts", "PURPLE"), ("CI & Scaffold", "GREEN"),
              ("PR Reporting", "PINK"), ("Tests & Cleanup", "YELLOW"),
              ("Runtime & Platform", "ORANGE"), ("Docs", "GRAY")]
SOURCES = [("CodeRabbit", "BLUE"), ("Gitar", "GREEN"), ("Both bots", "PURPLE")]


# --------------------------------------------------------------------- gh ----
def run(cmd: list[str], token: str | None = None, check: bool = True) -> str:
    env = dict(os.environ)
    if token:
        env["GH_TOKEN"] = token
    p = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if p.returncode and check:
        raise RuntimeError(f"{' '.join(cmd[:3])}… failed: {p.stderr.strip()[:400]}")
    return p.stdout


def api(path: str, jq: str | None = None, paginate: bool = True) -> object:
    cmd = ["gh", "api", path] + (["--paginate"] if paginate else [])
    if jq:
        cmd += ["--jq", jq]
    out = run(cmd).strip()
    if not out:
        return [] if jq else {}
    if jq:
        return [json.loads(x) for x in out.splitlines() if x.strip()]
    return json.loads(out)


def gql(query: str, token: str, **kw) -> dict:
    cmd = ["gh", "api", "graphql", "-f", f"query={query}"]
    for k, v in kw.items():
        # -F sends a typed literal; Int! parameters are rejected as strings.
        cmd += (["-F", f"{k}={v}"] if isinstance(v, int) else ["-f", f"{k}={v}"])
    return json.loads(run(cmd, token=token))


# ---------------------------------------------------------------- parsing ----
def strip_noise(body: str) -> str:
    """Drop the parts of a bot comment that are scaffolding, not the finding."""
    b = body
    for s in ("🧩 Analysis chain", "🤖 Prompt for AI Agents",
              "📝 Committable suggestion", "🛠️ Refactor suggestion"):
        b = re.sub(rf"<details>\s*<summary>{re.escape(s)}</summary>.*?</details>",
                   "", b, flags=re.S)
    b = re.sub(r"<!--.*?-->", "", b, flags=re.S)
    b = re.sub(r"<sub>.*?</sub>", "", b, flags=re.S)
    b = re.sub(r"^\s*- \[ \] Apply fix\s*$", "", b, flags=re.M)
    b = re.sub(r"</?(details|summary|kbd|b)>", "", b)
    return re.sub(r"\n{3,}", "\n\n", b).strip()


@dataclass
class Finding:
    bot: str            # CodeRabbit | Gitar
    path: str
    line: int | None
    title: str
    severity: str       # critical | major | minor
    kind: str           # security | bug | edge-case | quality | docs
    body: str
    url: str
    pr: int

    @property
    def fingerprint(self) -> str:
        norm = re.sub(r"[^a-z0-9]+", "-", self.title.lower()).strip("-")[:60]
        return hashlib.sha256(f"{self.path}|{norm}".encode()).hexdigest()[:16]


CR_HEAD = re.compile(r"^_([^_]+)_\s*\|\s*_([^_]+)_", re.M)
# Gitar writes the label as `<b>Quality:</b> …` — the colon sits inside the bold,
# not after it — but plain `Quality: …` also occurs. Accept the colon on either
# side, or the tags would be captured into the title.
GITAR_HEAD = re.compile(
    r"(?:⚠️|💡|🔒)\s*(?:<b>)?(Security|Bug|Quality|Edge Case|Performance|Correctness)"
    r"\s*:?\s*(?:</b>)?\s*:?\s*(.+?)(?:</summary>|\n|$)")
# CodeRabbit opens some comments with a classification label — "Reachability:",
# "Sensitive Data Exposure (CWE-200):" — before stating the actual claim. A bold
# run ending in a colon is one of those, so it is not the title.
CR_TITLE = re.compile(r"\*\*(.{8,160}?)\*\*", re.S)


def _severity(text: str) -> str:
    t = text.lower()
    if "critical" in t or "🔴" in text:
        return "critical"
    if "major" in t or "🟠" in text:
        return "major"
    return "minor"


def _kind(blob: str, path: str) -> str:
    t = blob.lower()
    if "security" in t or "cwe-" in t or "injection" in t or "secret" in t:
        return "security"
    # Prose is judged as prose. CodeRabbit files a wrong command in a .md under
    # "Functional Correctness", which would otherwise outrank a real code bug.
    if path.endswith((".md", ".rst", ".txt")):
        return "docs"
    if "bug" in t or "correctness" in t:
        return "bug"
    if "edge case" in t:
        return "edge-case"
    return "quality"


def parse(body: str, path: str, line: int | None, login: str,
          url: str, pr: int) -> list[Finding]:
    """One comment holds either one inline finding or several summary ones."""
    bot = "CodeRabbit" if "coderabbit" in login else "Gitar"
    clean = strip_noise(body)
    if not clean:
        return []
    # A skipped review, walkthrough or status note carries no finding.
    if (re.search(r"Review skipped|Currently processing|📝 Walkthrough|Summary by", body)
            and not GITAR_HEAD.search(body)):
        return []

    out: list[Finding] = []
    if bot == "CodeRabbit":
        m = CR_HEAD.search(clean)
        if not m:
            return []
        cat, sev = m.group(1), m.group(2)
        title = cat
        for cand in CR_TITLE.findall(clean[m.end():]):
            c = " ".join(cand.split())
            if not c.endswith(":"):
                title = c
                break
        title = title.strip().rstrip(".")
        out.append(Finding(bot, path, line, title, _severity(sev),
                           _kind(cat + " " + clean, path), clean, url, pr))
    else:
        for m in GITAR_HEAD.finditer(body):
            title = re.sub(r"\s+", " ", m.group(2)).strip()
            if not title:
                continue
            label = m.group(1)
            out.append(Finding(bot, path, line, title,
                               "major" if label in ("Security", "Bug") else "minor",
                               _kind(label + " " + clean, path), clean, url, pr))
            if path:      # an inline comment describes exactly one finding
                break
    return out


# ------------------------------------------------------- classification ----
def priority(f: Finding) -> str:
    if f.severity == "critical" or (f.severity == "major" and f.kind == "security"):
        return "P0 — Critical"
    if f.severity == "major" or f.kind == "bug":
        return "P1 — High"
    if f.kind == "docs":
        return "P3 — Low"
    return "P2 — Medium"


def category(f: Finding) -> str:
    p = f.path or ""
    if f.kind == "security":
        return "Security & Secrets"
    if re.search(r"projections/|tools/openmetadata|catalog_sync|recce", p):
        return "Catalog & Metadata"
    if re.search(r"toolkits/.+/(scripts|hooks)/", p):
        return "Toolkit Hooks & Scripts"
    if re.search(r"scaffold/|\.github/workflows|/ci\.py", p):
        return "CI & Scaffold"
    if re.search(r"/pr\.py$", p):
        return "PR Reporting"
    if re.search(r"(^|/)tests?/", p):
        return "Tests & Cleanup"
    if p.endswith((".md", ".rst", ".txt")):
        return "Docs"
    return "Runtime & Platform"


def labels_for(f: Finding) -> list[str]:
    out = [TRACKING_LABEL, "coderabbit" if f.bot == "CodeRabbit" else "gitar"]
    out.append("severity:major" if f.severity in ("critical", "major") else "severity:minor")
    if f.kind == "security":
        out.append("security")
    if f.kind in ("bug", "edge-case"):
        out.append("bug")
    if f.kind == "docs":
        out.append("documentation")
    return out


# ----------------------------------------------------------------- issues ----
def find_issue(fp: str) -> dict | None:
    return index().get(fp)


_INDEX: dict[str, dict] | None = None
_ALL: list[dict] = []


def index() -> dict[str, dict]:
    """Every tracked issue, keyed by each fingerprint in its body.

    Built once from the issues list endpoint rather than one search per finding:
    code search is capped at 30 requests a minute, which a PR carrying a dozen
    findings blows through immediately, and the failure is a 403 mid-run.
    """
    global _INDEX
    if _INDEX is not None:
        return _INDEX
    _INDEX = {}
    rows = api(f"repos/{REPO}/issues?labels={TRACKING_LABEL}&state=all&per_page=100", jq=".[]")
    for it in rows:
        if it.get("pull_request"):        # the issues endpoint also returns PRs
            continue
        _ALL.append(it)
        for fp in re.findall(rf"{re.escape(MARK)}([0-9a-f]+)", it.get("body") or ""):
            # An open issue wins over a closed one carrying the same marker.
            cur = _INDEX.get(fp)
            if cur is None or (cur.get("state") != "open" and it.get("state") == "open"):
                _INDEX[fp] = it
    print(f"  index: {len(_ALL)} tracked issue(s), {len(_INDEX)} fingerprint(s)")
    return _INDEX


def remember(issue: dict, fps: list[str]) -> None:
    """Keep the in-memory index true after a write, so one run stays consistent."""
    idx = index()
    for fp in fps:
        idx[fp] = issue
    if issue not in _ALL:
        _ALL.append(issue)


def related(path: str, skip_fp: str) -> list[dict]:
    """Other open findings on the same file.

    The two bots describe one defect in different words — "Branch header label
    is escaped twice" and "Escape the branch name only once" are the same bug —
    so a title fingerprint cannot merge them and this does not pretend to.
    Same-file findings are cross-linked instead, and a human decides whether two
    issues are really one.
    """
    if not path:
        return []
    index()
    return [it for it in _ALL
            if it.get("state") == "open"
            and path in (it.get("body") or "")
            and f"{MARK}{skip_fp}" not in (it.get("body") or "")]


def render(f: Finding, prior: str | None = None) -> str:
    cite = (f"### {f.bot} — [`{f.path}:{f.line}`]({f.url}) (PR #{f.pr})\n\n"
            if f.path else f"### {f.bot} — [PR #{f.pr}]({f.url})\n\n")
    block = cite + f.body
    if prior:
        # Same defect, second citation (the other bot, or a re-review).
        return prior.rstrip() + "\n\n---\n\n" + block if f.url not in prior else prior
    head = ("> Carried over from an automated PR review so it survives the PR "
            "being merged/closed.\n"
            "> **This issue stays open until the finding is resolved.**\n\n"
            f"<!-- {MARK}{f.fingerprint} -->\n\n"
            f"**Origin:** #{f.pr}\n\n")
    return head + block


def upsert(f: Finding) -> int | None:
    found = find_issue(f.fingerprint)
    labels = labels_for(f)
    if found:
        n = found["number"]
        body = render(f, found.get("body") or "")
        if body != (found.get("body") or ""):
            run(["gh", "issue", "edit", str(n), "--repo", REPO, "--body", body])
            found["body"] = body
        remember(found, [f.fingerprint])
        have = {x["name"] for x in found.get("labels", [])}
        add = [x for x in labels if x not in have]
        # A finding re-reported harder must not stay labelled minor.
        if "severity:major" in add and "severity:minor" in have:
            run(["gh", "issue", "edit", str(n), "--repo", REPO,
                 "--remove-label", "severity:minor"], check=False)
        if add:
            cmd = ["gh", "issue", "edit", str(n), "--repo", REPO]
            for lab in add:
                cmd += ["--add-label", lab]
            run(cmd, check=False)
        print(f"  updated #{n}  {f.title[:60]}")
        return n
    # A terse title ("Fail closed when the gate is unavailable") reads as an
    # instruction with no subject; the filename supplies the missing one.
    stem = pathlib.Path(f.path or "").name
    title = f.title if len(f.title) > 24 else f"{stem}: {f.title}"
    cmd = ["gh", "issue", "create", "--repo", REPO, "--title", title[:250],
           "--body", render(f)]
    for lab in labels:
        cmd += ["--label", lab]
    out = run(cmd).strip().splitlines()
    url = next((x for x in reversed(out) if x.startswith("http")), "")
    if not url:
        print(f"::warning::could not read new issue url for {f.title[:50]}")
        return None
    n = int(url.rsplit("/", 1)[1])
    print(f"  created #{n}  {title[:60]}")
    sibs = related(f.path, f.fingerprint)
    # Register before cross-linking, so two findings created in one run see each
    # other rather than both being filed as if they were the first.
    remember({"number": n, "title": title, "state": "open",
              "body": render(f), "labels": [{"name": x} for x in labels]},
             [f.fingerprint])
    if sibs:
        lines = "\n".join(f"- #{s['number']} — {s['title']}" for s in sibs[:8])
        note = (f"Other open findings on `{f.path}` — check whether any is this "
                f"same defect in the other bot's words:\n\n{lines}")
        run(["gh", "issue", "comment", str(n), "--repo", REPO, "--body", note],
            check=False)
    return n


# ------------------------------------------------------------- resolution ----
THREADS_Q = """
query($o:String!,$r:String!,$n:Int!){
  repository(owner:$o,name:$r){
    pullRequest(number:$n){
      merged
      mergeCommit{oid}
      headRefOid
      reviewThreads(first:100){
        nodes{
          isResolved
          path
          comments(first:1){nodes{body url createdAt author{login}}}
        }
      }
    }
  }
}"""


def fix_commit(path: str, since: str, head: str) -> dict | None:
    """The most recent commit touching `path` after the finding was raised.

    That is the change the reviewer resolved the thread against. It is reported
    as exactly that — the last change to the flagged file since the comment —
    rather than claimed to be a verified fix.
    """
    if not path:
        return None
    q = f"repos/{REPO}/commits?sha={head}&path={path}&since={since}&per_page=20"
    rows = api(q, jq=".[]", paginate=False)
    if not rows:
        return None
    c = rows[0]
    return {"sha": c["sha"], "url": c["html_url"],
            "msg": (c["commit"]["message"].splitlines() or [""])[0][:100]}


def close_resolved(pr: int) -> int:
    """Close the issues whose review threads the bots have marked resolved."""
    tok = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or ""
    data = gql(THREADS_Q, tok, o=OWNER, r=NAME, n=pr)["data"]["repository"]["pullRequest"]
    if not data:
        return 0
    merged, head = data.get("merged"), data.get("headRefOid") or ""
    merge_sha = (data.get("mergeCommit") or {}).get("oid")
    closed = 0
    for th in data["reviewThreads"]["nodes"]:
        if not th.get("isResolved"):
            continue
        cs = th["comments"]["nodes"]
        if not cs:
            continue
        c = cs[0]
        login = (c.get("author") or {}).get("login", "")
        if not any(b in login for b in BOTS):
            continue
        for f in parse(c["body"], th.get("path", ""), None, login, c["url"], pr):
            issue = find_issue(f.fingerprint)
            if not issue or issue.get("state") != "open":
                continue
            fc = fix_commit(th.get("path", ""), c["createdAt"], head)
            if fc:
                where = (f"[`{fc['sha'][:8]}`]({fc['url']}) — {fc['msg']}\n\n"
                         f"That is the most recent change to `{th.get('path')}` after the "
                         f"finding was raised, on the branch whose thread was resolved.")
            elif merged and merge_sha:
                where = (f"No commit touched `{th.get('path')}` after the finding was "
                         f"raised; the thread was resolved and the PR merged as "
                         f"[`{merge_sha[:8]}`](https://github.com/{REPO}/commit/{merge_sha}).")
            else:
                where = "The review thread was resolved; no fixing commit could be identified."
            body = (f"Closed automatically: the review thread for this finding was marked "
                    f"resolved on #{pr}.\n\n**Fixed in:** {where}\n\n"
                    f"Reference: {c['url']}\n\n"
                    f"If this was resolved without a real fix, reopen — nothing else will.")
            run(["gh", "issue", "comment", str(issue["number"]), "--repo", REPO,
                 "--body", body], check=False)
            run(["gh", "issue", "close", str(issue["number"]), "--repo", REPO,
                 "--reason", "completed"], check=False)
            print(f"  closed #{issue['number']}  ({f.title[:50]})")
            closed += 1
    return closed


def wait_for_checks(pr: int, budget: int = 900) -> None:
    """Hold until every other check on the PR has stopped running."""
    deadline = time.time() + budget
    while time.time() < deadline:
        out = run(["gh", "pr", "checks", str(pr), "--repo", REPO], check=False)
        pending = [x for x in out.splitlines() if "\tpending\t" in x]
        if not pending:
            return
        print(f"  waiting on {len(pending)} check(s)…")
        time.sleep(30)
    print("::warning::timed out waiting for checks; reconciling anyway")


# ------------------------------------------------------------------ board ----
def gql_options(opts: list[tuple[str, str]]) -> str:
    """Render select options as a GraphQL literal.

    Not json.dumps: GraphQL object keys are bare names, not strings, and `color`
    is an enum. JSON quotes both and the server rejects it with
    `Expected NAME, actual: STRING`.
    """
    return "[" + ", ".join(
        f'{{name: {json.dumps(n)}, color: {c}, description: ""}}' for n, c in opts) + "]"


def ensure_board():
    if not PROJECT_TOKEN:
        print("::warning::PROJECTS_TOKEN not set — issues tracked, board skipped")
        return None
    nodes = gql('query($l:String!){organization(login:$l){projectsV2(first:100)'
                '{nodes{id title number}}}}', PROJECT_TOKEN,
                l=OWNER)["data"]["organization"]["projectsV2"]["nodes"]
    proj = next((p for p in nodes if p["title"] == PROJECT_TITLE), None)
    if not proj:
        oid = gql('query($l:String!){organization(login:$l){id}}',
                  PROJECT_TOKEN, l=OWNER)["data"]["organization"]["id"]
        proj = gql('mutation($o:ID!,$t:String!){createProjectV2(input:{ownerId:$o,title:$t})'
                   '{projectV2{id title number}}}', PROJECT_TOKEN, o=oid,
                   t=PROJECT_TITLE)["data"]["createProjectV2"]["projectV2"]
        rid = gql('query($o:String!,$r:String!){repository(owner:$o,name:$r){id}}',
                  PROJECT_TOKEN, o=OWNER, r=NAME)["data"]["repository"]["id"]
        # A ProjectV2 belongs to the org; linking is what puts it on the repo tab.
        gql('mutation($p:ID!,$r:ID!){linkProjectV2ToRepository(input:{projectId:$p,'
            'repositoryId:$r}){repository{id}}}', PROJECT_TOKEN, p=proj["id"], r=rid)
        print(f"created project #{proj['number']} and linked it to {REPO}")

    fields = gql('query($p:ID!){node(id:$p){... on ProjectV2{fields(first:50){nodes{'
                 '... on ProjectV2SingleSelectField{id name options{id name}}}}}}}',
                 PROJECT_TOKEN, p=proj["id"])["data"]["node"]["fields"]["nodes"]
    have = {f["name"]: f for f in fields if f.get("name")}
    for fname, opts in (("Priority", PRIORITIES), ("Category", CATEGORIES),
                        ("Source", SOURCES)):
        if fname in have:
            continue
        payload = gql_options(opts)
        made = gql('mutation($p:ID!,$n:String!){createProjectV2Field(input:{projectId:$p,'
                   'dataType:SINGLE_SELECT,name:$n,singleSelectOptions:' + payload + '}){'
                   'projectV2Field{... on ProjectV2SingleSelectField{id name options{id name}}}}}',
                   PROJECT_TOKEN, p=proj["id"], n=fname)
        have[fname] = made["data"]["createProjectV2Field"]["projectV2Field"]
        print(f"  field {fname} created")
    return proj["id"], have


def file_on_board(board, issue_no: int, f: Finding, both: bool) -> None:
    if not board or not issue_no:
        return
    pid, fields = board
    nid = gql('query($o:String!,$r:String!,$n:Int!){repository(owner:$o,name:$r)'
              '{issue(number:$n){id}}}', PROJECT_TOKEN, o=OWNER, r=NAME,
              n=issue_no)["data"]["repository"]["issue"]["id"]
    item = gql('mutation($p:ID!,$c:ID!){addProjectV2ItemById(input:{projectId:$p,'
               'contentId:$c}){item{id}}}', PROJECT_TOKEN, p=pid,
               c=nid)["data"]["addProjectV2ItemById"]["item"]["id"]
    want = {"Priority": priority(f), "Category": category(f),
            "Source": "Both bots" if both else f.bot}
    for fname, oname in want.items():
        fld = fields.get(fname)
        opt = next((o for o in (fld or {}).get("options", []) if o["name"] == oname), None)
        if not fld or not opt:
            continue
        gql('mutation($p:ID!,$i:ID!,$f:ID!,$o:String!){updateProjectV2ItemFieldValue('
            'input:{projectId:$p,itemId:$i,fieldId:$f,value:{singleSelectOptionId:$o}})'
            '{projectV2Item{id}}}', PROJECT_TOKEN, p=pid, i=item, f=fld["id"], o=opt["id"])
    print(f"    board: {want['Priority']} / {want['Category']} / {want['Source']}")


# ------------------------------------------------------------------- main ----
def collect(pr: int) -> list[Finding]:
    out: list[Finding] = []
    for c in api(f"repos/{REPO}/pulls/{pr}/comments?per_page=100", jq=".[]"):
        if any(b in c["user"]["login"] for b in BOTS):
            out += parse(c["body"], c.get("path", ""),
                         c.get("line") or c.get("original_line"),
                         c["user"]["login"], c["html_url"], pr)
    for c in api(f"repos/{REPO}/issues/{pr}/comments?per_page=100", jq=".[]"):
        if any(b in c["user"]["login"] for b in BOTS):
            out += parse(c["body"], "", None, c["user"]["login"], c["html_url"], pr)
    return out


def track(findings: list[Finding]) -> None:
    if not findings:
        print("no findings to track")
        return
    groups: dict[str, list[Finding]] = {}
    for f in findings:
        groups.setdefault(f.fingerprint, []).append(f)
    board = ensure_board()
    print(f"{len(groups)} distinct finding(s)")
    rank = {"critical": 0, "major": 1, "minor": 2}
    for fs in groups.values():
        both = len({f.bot for f in fs}) > 1
        lead = min(fs, key=lambda f: rank[f.severity])
        n = None
        for f in fs:
            n = upsert(f) or n
        file_on_board(board, n, lead, both)


def prs_from_event(ev: dict, name: str) -> list[int]:
    if name == "workflow_run":
        wr = ev.get("workflow_run") or {}
        nums = [p["number"] for p in (wr.get("pull_requests") or [])]
        if nums:
            return nums
        sha = wr.get("head_sha")
        if sha:
            res = api(f"repos/{REPO}/commits/{sha}/pulls?per_page=10", jq=".[]")
            return [p["number"] for p in res if p.get("state") == "open"] or \
                   [p["number"] for p in res]
        return []
    if name == "pull_request":
        return [ev.get("pull_request", {}).get("number")]
    return []


def main() -> int:
    name = os.environ.get("GITHUB_EVENT_NAME", "")
    ev = {}
    p = os.environ.get("GITHUB_EVENT_PATH")
    if p and pathlib.Path(p).exists():
        ev = json.loads(pathlib.Path(p).read_text())

    # A single new comment: track it immediately, so a finding is never lost
    # even if the reconcile pass never runs.
    if name in ("pull_request_review_comment", "issue_comment"):
        c = ev.get("comment", {})
        login = c.get("user", {}).get("login", "")
        if not any(b in login for b in BOTS):
            print(f"not a tracked bot ({login})")
            return 0
        if name == "issue_comment" and not (ev.get("issue") or {}).get("pull_request"):
            print("comment is on an issue, not a PR")
            return 0
        pr = (ev.get("pull_request") or ev.get("issue") or {}).get("number")
        track(parse(c.get("body", ""), c.get("path", ""),
                    c.get("line") or c.get("original_line"),
                    login, c.get("html_url", ""), pr))
        return 0

    # Reconcile: every other pipeline has finished. File what is new, close
    # what the bots have since marked resolved.
    if name in ("workflow_run", "pull_request"):
        prs = [n for n in prs_from_event(ev, name) if n]
    else:
        target = os.environ.get("PR", "").strip()
        if target.isdigit():
            prs = [int(target)]
        else:
            state = "all" if target == "all" else "open"
            prs = [x["number"] for x in
                   api(f"repos/{REPO}/pulls?state={state}&per_page=100", jq=".[]")]

    if not prs:
        print("no pull request in scope")
        return 0
    print(f"reconciling {len(prs)} PR(s): {prs}")
    for pr in prs:
        print(f"— PR #{pr}")
        if name in ("workflow_run", "pull_request"):
            wait_for_checks(pr)
        track(collect(pr))
        n = close_resolved(pr)
        print(f"  {n} issue(s) closed as fixed")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:                                    # noqa: BLE001
        print(f"::error::{e}")
        sys.exit(1)
