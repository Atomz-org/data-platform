#!/usr/bin/env python3
"""Nightly issue hygiene for review findings: merge duplicates, fill the sidebar.

`bot_findings.py` files each review finding as an issue the moment it is
raised. Two things it cannot do from inside one pull request, this does once a
night over every open finding:

1. **Duplicates.** One defect reaches the tracker more than once — two bots,
   an inline comment and a review body, a run that raced another, a finding
   re-raised after a rebase. Candidates are issues that name the *same file*
   under the *same title* (or share a fingerprint). A candidate is only closed
   when the finding text agrees too:

       same fingerprint, or text similarity >= 0.75   duplicate: the newer is
                                                      closed as a duplicate of
                                                      the oldest, its labels and
                                                      fingerprints merged in
       text similarity >= 0.45, or either issue is    `possible-duplicate`: a
       a bundle of several findings (a Gitar summary)
                                                      person decides; nothing
                                                      is closed
       anything less                                  different defects

   The text check matters. The older parser titled findings by their CWE class,
   so "Authorization Bypass (CWE-693)" names several unrelated defects; a title
   match alone would have closed real bugs. A person who disagrees adds
   `not-duplicate` to either issue and the pair is never touched again.

2. **The sidebar**, from the labels — labels are what a finding is filed with,
   so they are the source; everything below is derived and re-derived nightly:

       labels     priority:*, area:*, effort:* back-filled on findings filed
                  before those labels existed (from severity/kind/file)
       Type       Bug for a bug or security finding, Task otherwise — only
                  when unset, so a person's choice stands
       Priority   the org issue field, from priority:P0..P3 → Urgent/High/
                  Medium/Low
       Effort     the org issue field, from effort:quick-win/heavy-lift → Low/
                  High
       Relationships  the finding's category epic as its parent
       Projects   the findings board, with Priority / Category / Source — only
                  with PROJECTS_TOKEN; GITHUB_TOKEN cannot reach an org project
       Assignees  the author of the pull request the finding was raised on,
                  when nobody is assigned and the author is a person

   Milestone is left alone: nothing about a finding says which one it belongs
   to, and a guessed milestone is worse than none.

Idempotent: a second run the same night changes nothing. `DRY_RUN=1` prints
every change instead of making it.
"""

from __future__ import annotations

import difflib
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import bot_findings as bf  # noqa: E402

DRY_RUN = bool(os.environ.get("DRY_RUN") or os.environ.get("BOT_FINDINGS_DRY_RUN"))
bf.DRY_RUN = DRY_RUN

#: A PAT (or app token) for the org-level parts. The org issue fields and the
#: project board are organisation objects; the repository's GITHUB_TOKEN may be
#: refused on them, and then the rest of the run still does what it can.
ORG_TOKEN = os.environ.get("ISSUE_FIELDS_TOKEN") or os.environ.get("PROJECTS_TOKEN") or ""
ASSIGN = os.environ.get("HYGIENE_ASSIGN_PR_AUTHOR", "1") not in ("0", "", "false")

POSSIBLE = "possible-duplicate"
NOT_DUP = "not-duplicate"
SAME, MAYBE = 0.75, 0.45

PRIORITY_FIELD = {"priority:P0": "Urgent", "priority:P1": "High", "priority:P2": "Medium", "priority:P3": "Low"}
EFFORT_FIELD = {"effort:quick-win": "Low", "effort:heavy-lift": "High"}

EXTRA_LABELS = [
    (POSSIBLE, "fbca04", "Looks like another finding; a person decides"),
    (NOT_DUP, "0e8a16", "A person decided this is not a duplicate; the nightly sweep leaves it alone"),
]

TALLY: dict[str, list[str]] = {
    k: [] for k in ("closed", "flagged", "labelled", "typed", "fields", "parented", "boarded", "assigned", "warnings")
}


def say(kind: str, line: str) -> None:
    TALLY[kind].append(line)
    print(("  WOULD " if DRY_RUN else "  ") + line)


def warn(line: str) -> None:
    TALLY["warnings"].append(line)
    print(f"::warning::{line}")


# ------------------------------------------------------------------ issues --
def open_findings() -> list[dict]:
    out = bf.run(
        [
            "gh",
            "issue",
            "list",
            "--repo",
            bf.REPO,
            "--label",
            bf.TRACKING_LABEL,
            "--state",
            "open",
            "--limit",
            "2000",
            "--json",
            "number,title,body,labels,assignees,createdAt,id",
        ]
    )
    return json.loads(out or "[]")


def labels_of(i: dict) -> set[str]:
    return {x["name"] for x in i.get("labels", [])}


_FILE = re.compile(r"^\*\*File:\*\* `([^`]+)`", re.M)
_HEAD = re.compile(r"^### [^\n]*?\[`([^`]+)`\]", re.M)


def path_of(i: dict) -> str:
    """The file a finding names — from `**File:**`, or the heading the older
    format used. A trailing `:line` or `:span` is not part of the file."""
    body = i.get("body") or ""
    m = _FILE.search(body) or _HEAD.search(body)
    return re.sub(r":\d+(?:-\d+)?$", "", m.group(1)) if m else ""


def fingerprints(i: dict) -> set[str]:
    return set(re.findall(rf"<!-- {re.escape(bf.MARK)}([0-9a-f]+) -->", i.get("body") or ""))


def title_key(i: dict) -> str:
    t = re.sub(r"^[\w./-]+\.\w+: ", "", i.get("title") or "")  # "file.py: short title"
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")[:60]


def finding_text(i: dict) -> str:
    """The defect as the reviewer stated it, without the tracker's framing,
    links, markers or the classification line — what two reports of one defect
    share and two defects under one title do not."""
    body = i.get("body") or ""
    parts = re.split(r"^### .*$", body, maxsplit=1, flags=re.M)
    text = parts[1] if len(parts) > 1 else body
    text = re.split(r"^---\s*$|^### ", text, maxsplit=1, flags=re.M)[0]
    text = re.sub(r"<!--.*?-->|\(https?://[^)]*\)|https?://\S+|^_.*_\s*\|.*$", " ", text, flags=re.M | re.S)
    return " ".join(re.findall(r"[a-z0-9_]+", text.lower()))[:1500]


def similarity(a: dict, b: dict) -> float:
    if fingerprints(a) & fingerprints(b):
        return 1.0
    ta, tb = finding_text(a), finding_text(b)
    if not ta or not tb:
        return 0.0
    return difflib.SequenceMatcher(None, ta.split(), tb.split(), autojunk=False).ratio()


# -------------------------------------------------------------- duplicates --
def duplicate_groups(issues: list[dict]) -> list[list[tuple[dict, float]]]:
    """Per candidate group: the canonical (oldest) issue first, then each other
    member with its similarity to the canonical."""
    by_title: dict[str, list[dict]] = {}
    for i in issues:
        if labels_of(i) & {NOT_DUP, bf.EPIC_LABEL}:
            continue
        by_title.setdefault(title_key(i), []).append(i)
    groups: list[list[dict]] = []
    for same in by_title.values():
        if len(same) < 2:
            continue
        # A report with no file — a review-body or walkthrough restatement —
        # joins the title's group only when that title names exactly one file.
        # The same sentence about two files is two defects, and a pathless
        # report cannot say which of them it meant. The tracker's own `locate`
        # applies this rule; the sweep agrees with it rather than inventing one.
        pathless = [i for i in same if not path_of(i)]
        paths = sorted({path_of(i) for i in same if path_of(i)})
        if not paths:
            groups.append(pathless)
        for p in paths:
            groups.append([i for i in same if path_of(i) == p] + (pathless if len(paths) == 1 else []))
    # A shared fingerprint joins issues whatever their titles now say.
    by_fp: dict[str, list[dict]] = {}
    for i in issues:
        for fp in fingerprints(i):
            by_fp.setdefault(fp, []).append(i)
    groups += [g for g in by_fp.values() if len({x["number"] for x in g}) > 1]
    seen: set[frozenset[int]] = set()
    out = []
    for g in groups:
        members = sorted({x["number"]: x for x in g}.values(), key=lambda x: x["number"])
        ids = frozenset(x["number"] for x in members)
        if ids in seen or len(ids) < 2:
            continue
        seen.add(ids)
        canon = members[0]
        out.append([(canon, 1.0)] + [(m, similarity(canon, m)) for m in members[1:]])
    return out


def close_duplicate(canon: dict, dup: dict, score: float) -> None:
    n, c = dup["number"], canon["number"]
    say("closed", f"close #{n} as a duplicate of #{c} (similarity {score:.2f}) — {dup['title'][:60]}")
    if DRY_RUN:
        return
    # The canonical inherits what made the duplicate findable: its fingerprints,
    # so the next report of it lands on the survivor, and its labels, raised.
    body = canon.get("body") or ""
    missing = [fp for fp in fingerprints(dup) if fp not in body]
    note = f"\n\n> Also reported as #{n}, closed by the nightly sweep as a duplicate of this issue."
    if missing or f"#{n}," not in body:
        marks = "".join(f"\n<!-- {bf.MARK}{fp} -->" for fp in missing)
        body = body + note + marks
        bf.run(["gh", "issue", "edit", str(c), "--repo", bf.REPO, "--body", body])
        canon["body"] = body
    add, remove = bf.relabel(labels_of(canon), sorted(labels_of(dup) - {POSSIBLE, bf.DUPLICATE_LABEL}))
    if add or remove:
        cmd = ["gh", "issue", "edit", str(c), "--repo", bf.REPO]
        for x in add:
            cmd += ["--add-label", x]
        for x in remove:
            cmd += ["--remove-label", x]
        bf.run(cmd, check=False)
        canon["labels"] = [{"name": x} for x in (labels_of(canon) | set(add)) - set(remove)]
    bf.run(
        [
            "gh",
            "issue",
            "comment",
            str(n),
            "--repo",
            bf.REPO,
            "--body",
            f"Duplicate of #{c}. Closed by the nightly issue sweep: same file, same title, and the finding "
            f"text agrees ({score:.0%}). If they are different defects, reopen this and add `{NOT_DUP}` — "
            f"the sweep will leave the pair alone.",
        ],
        check=False,
    )
    bf.run(["gh", "issue", "edit", str(n), "--repo", bf.REPO, "--add-label", bf.DUPLICATE_LABEL], check=False)
    # `duplicate` is a close reason GitHub renders as "Closed as duplicate";
    # a server that does not know it gets `not_planned`, which still stops the
    # issue counting as open work.
    try:
        bf.run(
            [
                "gh",
                "api",
                "-X",
                "PATCH",
                f"repos/{bf.REPO}/issues/{n}",
                "-f",
                "state=closed",
                "-f",
                "state_reason=duplicate",
            ]
        )
    except RuntimeError:
        bf.run(["gh", "issue", "close", str(n), "--repo", bf.REPO, "--reason", "not planned"], check=False)


def flag_possible(canon: dict, other: dict, score: float) -> None:
    n = other["number"]
    if POSSIBLE in labels_of(other):
        return
    say("flagged", f"flag #{n} as a possible duplicate of #{canon['number']} (similarity {score:.2f})")
    if DRY_RUN:
        return
    bf.run(["gh", "issue", "edit", str(n), "--repo", bf.REPO, "--add-label", POSSIBLE], check=False)
    bf.run(
        [
            "gh",
            "issue",
            "comment",
            str(n),
            "--repo",
            bf.REPO,
            "--body",
            f"Possibly the same defect as #{canon['number']}: same file and title, finding text "
            f"{score:.0%} similar. Not closed — a person decides. Close this as a duplicate, or add "
            f"`{NOT_DUP}` to keep both.",
        ],
        check=False,
    )


_BUNDLE = re.compile(r"/\s*(\d+)\s+findings?", re.I)


def bundled(i: dict) -> bool:
    """Whether an issue carries more than one finding — a Gitar review summary
    filed whole. Closing one as a duplicate of the single inline finding it
    shares would take the others with it, so a bundle is at most flagged."""
    body = i.get("body") or ""
    m = _BUNDLE.search(body)
    return bool(m and int(m.group(1)) > 1) or len(bf.GITAR_HEAD.findall(body)) > 1


def dedupe(issues: list[dict]) -> set[int]:
    """Returns the issue numbers closed, so the sidebar pass skips them."""
    closed: set[int] = set()
    for group in duplicate_groups(issues):
        canon = group[0][0]
        for other, score in group[1:]:
            if score >= SAME and not (bundled(canon) or bundled(other)):
                close_duplicate(canon, other, score)
                closed.add(other["number"])
            elif score >= MAYBE:
                flag_possible(canon, other, score)
    return closed


# ----------------------------------------------------------------- sidebar --
def as_finding(i: dict) -> bf.Finding:
    """The issue, read back into the shape `bot_findings` labels from."""
    labs = labels_of(i)
    kind = (
        "security"
        if "security" in labs
        else "bug"
        if "bug" in labs
        else "docs"
        if "documentation" in labs
        else "quality"
    )
    sev = "major" if "severity:major" in labs else "minor"
    bot = "CodeRabbit" if "coderabbit" in labs else "Gitar" if "gitar" in labs else "Reviewer"
    section = "nitpick" if "nitpick" in labs else "outside-diff" if "outside-diff" in labs else ""
    return bf.Finding(
        bot,
        path_of(i),
        None,
        i.get("title") or "",
        sev,
        kind,
        i.get("body") or "",
        "",
        0,
        section=section,
        effort=bf._effort(i.get("body") or ""),
    )


def backfill_labels(i: dict) -> None:
    want = [x for x in bf.labels_for(as_finding(i)) if x.startswith(("priority:", "area:", "effort:"))]
    add, remove = bf.relabel(labels_of(i), want)
    if not (add or remove):
        return
    say("labelled", f"#{i['number']} +{add or '[]'} -{remove or '[]'}")
    if DRY_RUN:
        i["labels"] = [{"name": x} for x in (labels_of(i) | set(add)) - set(remove)]
        return
    cmd = ["gh", "issue", "edit", str(i["number"]), "--repo", bf.REPO]
    for x in add:
        cmd += ["--add-label", x]
    for x in remove:
        cmd += ["--remove-label", x]
    bf.run(cmd, check=False)
    i["labels"] = [{"name": x} for x in (labels_of(i) | set(add)) - set(remove)]


def issue_state(numbers: list[int], token: str) -> dict[int, dict]:
    """Type, org field values and parent for many issues, in batches."""
    out: dict[int, dict] = {}
    for k in range(0, len(numbers), 50):
        chunk = numbers[k : k + 50]
        parts = " ".join(
            f"i{n}: issue(number:{n}){{number issueType{{name}} parent{{number}} "
            f"issueFieldValues(first:10){{nodes{{... on IssueFieldSingleSelectValue{{name "
            f"field{{... on IssueFieldSingleSelect{{name}}}}}}}}}}}}"
            for n in chunk
        )
        q = f'{{repository(owner:"{bf.OWNER}",name:"{bf.NAME}"){{{parts}}}}}'
        try:
            data = bf.gql(q, token)["data"]["repository"]
        except Exception as exc:  # noqa: BLE001
            warn(f"could not read issue types/fields: {str(exc)[:160]}")
            return out
        for v in data.values():
            if v:
                out[v["number"]] = v
    return out


def org_fields(token: str) -> dict[str, dict]:
    q = (
        f'{{organization(login:"{bf.OWNER}"){{issueFields(first:30){{nodes{{'
        f"... on IssueFieldSingleSelect{{id name options{{id name}}}}}}}}}}}}"
    )
    try:
        nodes = bf.gql(q, token)["data"]["organization"]["issueFields"]["nodes"]
    except Exception as exc:  # noqa: BLE001
        warn(f"org issue fields unreadable ({str(exc)[:120]}); set ISSUE_FIELDS_TOKEN")
        return {}
    return {n["name"]: n for n in nodes if n and n.get("name")}


def set_type(i: dict, state: dict) -> None:
    if (state.get("issueType") or {}).get("name"):
        return  # a person's choice, or ours from last night
    labs = labels_of(i)
    want = "Bug" if labs & {"bug", "security"} else "Task"
    say("typed", f"#{i['number']} type → {want}")
    if not DRY_RUN:
        try:
            bf.run(
                ["gh", "api", "-X", "PATCH", f"repos/{bf.REPO}/issues/{i['number']}", "-f", f"type={want}"],
                token=ORG_TOKEN or None,
            )
        except RuntimeError as exc:
            warn(f"#{i['number']}: could not set type ({str(exc)[:120]})")


def set_fields(i: dict, state: dict, fields: dict[str, dict]) -> None:
    labs = labels_of(i)
    have = {
        (v.get("field") or {}).get("name"): v.get("name")
        for v in ((state.get("issueFieldValues") or {}).get("nodes") or [])
        if v
    }
    wants = {
        "Priority": next((PRIORITY_FIELD[x] for x in labs if x in PRIORITY_FIELD), None),
        "Effort": next((EFFORT_FIELD[x] for x in labs if x in EFFORT_FIELD), None),
    }
    values = []
    for name, value in wants.items():
        f = fields.get(name)
        if not value or not f or have.get(name) == value:
            continue
        opt = next((o["id"] for o in f.get("options") or [] if o["name"] == value), None)
        if opt:
            values.append((name, value, f["id"], opt))
    if not values:
        return
    say("fields", f"#{i['number']} " + ", ".join(f"{n} → {v}" for n, v, _, _ in values))
    if DRY_RUN:
        return
    items = ",".join(f'{{fieldId:"{fid}",singleSelectOptionId:"{oid}"}}' for _, _, fid, oid in values)
    try:
        bf.gql(
            f'mutation{{setIssueFieldValue(input:{{issueId:"{i["id"]}",issueFields:[{items}]}}){{clientMutationId}}}}',
            ORG_TOKEN or os.environ.get("GH_TOKEN", ""),
        )
    except Exception as exc:  # noqa: BLE001
        warn(f"#{i['number']}: could not set issue fields ({str(exc)[:120]}); set ISSUE_FIELDS_TOKEN")


def set_parent(i: dict, state: dict) -> None:
    if (state.get("parent") or {}).get("number"):
        return
    cat = bf.category(as_finding(i))
    say("parented", f"#{i['number']} parent → epic '{cat}'")
    if not DRY_RUN:
        bf.adopt(bf.ensure_epic(cat), i["number"])


_ORIGIN = re.compile(r"\*\*(?:Raised on|Origin):\*\*\s*#(\d+)")
_AUTHORS: dict[int, str] = {}


def assign_author(i: dict) -> None:
    if not ASSIGN or i.get("assignees"):
        return
    m = _ORIGIN.search(i.get("body") or "")
    if not m:
        return
    pr = int(m.group(1))
    if pr not in _AUTHORS:
        try:
            user = (bf.api(f"repos/{bf.REPO}/pulls/{pr}", paginate=False) or {}).get("user") or {}
            _AUTHORS[pr] = "" if user.get("type") == "Bot" else user.get("login", "")
        except RuntimeError:
            _AUTHORS[pr] = ""
    who = _AUTHORS[pr]
    if not who:
        return
    say("assigned", f"#{i['number']} assignee → @{who} (author of #{pr})")
    if not DRY_RUN:
        bf.run(["gh", "issue", "edit", str(i["number"]), "--repo", bf.REPO, "--add-assignee", who], check=False)


def put_on_board(board, i: dict) -> None:
    if board is None:
        return
    f = as_finding(i)
    both = {"coderabbit", "gitar"} <= labels_of(i)
    bf.file_on_board(board, i["number"], f, both, landed=bf.LANDED_LABEL in labels_of(i))
    TALLY["boarded"].append(f"#{i['number']}")


# -------------------------------------------------------------------- main --
def summary() -> None:
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    lines = [f"## Issue hygiene{' (dry run)' if DRY_RUN else ''}", "", "| | |", "|---|--:|"]
    names = {
        "closed": "duplicates closed",
        "flagged": "possible duplicates flagged",
        "labelled": "labels back-filled",
        "typed": "types set",
        "fields": "Priority/Effort fields set",
        "parented": "epics attached",
        "boarded": "on the board",
        "assigned": "assigned",
        "warnings": "warnings",
    }
    lines += [f"| {names[k]} | {len(v)} |" for k, v in TALLY.items()]
    for k in ("closed", "flagged", "warnings"):
        if TALLY[k]:
            lines += ["", f"**{names[k].capitalize()}**", *[f"- {x}" for x in TALLY[k][:40]]]
    text = "\n".join(lines) + "\n"
    print(text)
    if path:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(text)


def main() -> int:
    if not DRY_RUN:
        bf.ensure_labels()
        have = {x["name"] for x in bf.api(f"repos/{bf.REPO}/labels?per_page=100", jq=".[]")}
        for name, colour, desc in EXTRA_LABELS:
            if name not in have:
                bf.run(
                    ["gh", "label", "create", name, "--repo", bf.REPO, "--color", colour, "--description", desc],
                    check=False,
                )
    issues = open_findings()
    print(f"{len(issues)} open finding(s)")

    closed = dedupe(issues)
    live = [i for i in issues if i["number"] not in closed and bf.EPIC_LABEL not in labels_of(i)]

    token = ORG_TOKEN or os.environ.get("GH_TOKEN", "")
    fields = org_fields(token)
    states = issue_state([i["number"] for i in live], token)
    board = bf.ensure_board() if bf.PROJECT_TOKEN else None
    if board is None:
        warn("PROJECTS_TOKEN not set — the Projects field is left empty (GITHUB_TOKEN cannot reach an org project)")

    for i in live:
        st = states.get(i["number"], {})
        try:
            backfill_labels(i)
            set_type(i, st)
            set_fields(i, st, fields)
            set_parent(i, st)
            assign_author(i)
            put_on_board(board, i)
        except Exception as exc:  # noqa: BLE001 — one bad issue must not stop the sweep
            warn(f"#{i['number']}: {str(exc)[:160]}")
    summary()
    return 0


if __name__ == "__main__":
    sys.exit(main())
