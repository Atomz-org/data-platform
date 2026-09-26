"""Snapshot a Confluence page as Markdown — the REST fallback when the Atlassian
Rovo MCP server is not connected.

    uv run python confluence_fetch.py <page-url-or-id> [--children] [--api v2|v1]
                                      [--out requirements/REQ-<id>/source.md]
    uv run python confluence_fetch.py --from-file export.html --out source.md

Credentials come from the environment only — CONFLUENCE_BASE_URL,
CONFLUENCE_EMAIL, CONFLUENCE_API_TOKEN (Cloud: basic auth with an API token;
Server/Data Center: set CONFLUENCE_PAT for a bearer token instead). Nothing
here writes a credential to disk.

Storage-format XHTML is converted with the standard library: headings, lists,
tables as pipe tables, code/SQL macros as fenced blocks, status lozenges and
info/warning panels as labelled text. The output's frontmatter carries the page
id, version, URL and a sha256 of the body so a later fetch can tell whether the
requirement changed.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path

PANELS = {"info", "note", "warning", "tip", "panel", "expand"}


# ------------------------------------------------------------ conversion ----
class _Storage(HTMLParser):
    """Confluence storage XHTML → Markdown. Tolerant: unknown tags pass their text."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.out: list[str] = []
        self.lists: list[str] = []          # "ul" / "ol" stack
        self.ol_n: list[int] = []
        self.table: list[list[str]] | None = None
        self.cell: list[str] | None = None
        self.macro: list[str] = []          # structured-macro name stack
        self.param: str | None = None
        self.params: dict[str, str] = {}
        self.code: list[str] | None = None
        self.href: str | None = None
        self.link_text: list[str] = []
        self.panels = 0                     # open info/warning panels → blockquote

    # text sinks, innermost first
    def _emit(self, text: str) -> None:
        if self.code is not None:
            self.code.append(text)
        elif self.href is not None:
            self.link_text.append(text)
        elif self.cell is not None:
            self.cell.append(text)
        else:
            self.out.append(text)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = dict(attrs)
        if re.fullmatch(r"h[1-6]", tag):
            self._emit("\n\n" + "#" * int(tag[1]) + " ")
        elif tag == "p":
            self._emit(" " if self.cell is not None else "\n> " if self.panels else "\n\n")
        elif tag == "br":
            self._emit("\n" if self.cell is None else " ")
        elif tag in {"ul", "ol"}:
            if not self.lists:
                self._emit("\n")
            self.lists.append(tag)
            self.ol_n.append(0)
        elif tag == "li":
            depth = len(self.lists) - 1
            if self.lists and self.lists[-1] == "ol":
                self.ol_n[-1] += 1
                bullet = f"{self.ol_n[-1]}."
            else:
                bullet = "-"
            self._emit("\n" + "  " * max(depth, 0) + bullet + " ")
        elif tag in {"strong", "b"}:
            self._emit("**")
        elif tag in {"em", "i"}:
            self._emit("_")
        elif tag == "code" and self.code is None:
            self._emit("`")
        elif tag == "a":
            self.href, self.link_text = a.get("href") or "", []
        elif tag == "table":
            self.table = []
        elif tag == "tr" and self.table is not None:
            self.table.append([])
        elif tag in {"td", "th"} and self.table is not None:
            self.cell = []
        elif tag == "ac:structured-macro":
            name = a.get("ac:name") or ""
            self.macro.append(name)
            self.params = {}
            if name in {"code", "noformat"}:
                self.code = []
            elif name in PANELS:
                self.panels += 1
                self._emit(f"\n\n> **{name.upper()}:**")
        elif tag == "ac:parameter":
            self.param = a.get("ac:name") or ""
        elif tag == "ri:page":
            self._emit(f"[[{a.get('ri:content-title', '')}]]")
        elif tag == "ri:attachment":
            self._emit(f"[attachment: {a.get('ri:filename', '')}]")
        elif tag == "ri:user":
            self._emit("@user")
        elif tag == "time":
            self._emit(a.get("datetime") or "")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"ul", "ol"} and self.lists:
            self.lists.pop()
            self.ol_n.pop()
            if not self.lists:
                self._emit("\n")
        elif tag in {"strong", "b"}:
            self._emit("**")
        elif tag in {"em", "i"}:
            self._emit("_")
        elif tag == "code" and self.code is None:
            self._emit("`")
        elif tag == "a" and self.href is not None:
            text, href = "".join(self.link_text).strip(), self.href
            self.href = None
            self._emit(f"[{text or href}]({href})" if href else text)
        elif tag in {"td", "th"} and self.cell is not None and self.table is not None:
            text = re.sub(r"\s+", " ", "".join(self.cell)).strip().replace("|", "\\|")
            if self.table:
                self.table[-1].append(text)
            self.cell = None
        elif tag == "table" and self.table is not None:
            rows = [r for r in self.table if r]
            self.table = None
            if rows:
                width = max(len(r) for r in rows)
                rows = [r + [""] * (width - len(r)) for r in rows]
                md = ["| " + " | ".join(rows[0]) + " |", "|" + "---|" * width]
                md += ["| " + " | ".join(r) + " |" for r in rows[1:]]
                self._emit("\n\n" + "\n".join(md) + "\n")
        elif tag == "ac:parameter":
            self.param = None
        elif tag == "ac:structured-macro" and self.macro:
            name = self.macro.pop()
            if name in {"code", "noformat"} and self.code is not None:
                body, self.code = "".join(self.code).strip("\n"), None
                self._emit(f"\n\n```{self.params.get('language', '')}\n{body}\n```\n")
            elif name in PANELS:
                self.panels -= 1
                self._emit("\n\n")
            elif name == "status":
                self._emit(f"[{self.params.get('title', '').upper()}]")
            elif name == "jira":
                self._emit(f"[{self.params.get('key', 'jira')}]")

    def handle_data(self, data: str) -> None:
        if self.param is not None:
            self.params[self.param] = self.params.get(self.param, "") + data
            return
        if self.code is not None:
            self.code.append(data)
            return
        self._emit(re.sub(r"[ \t\r\n]+", " ", data))

    def markdown(self) -> str:
        text = "".join(self.out)
        text = re.sub(r"[ \t]+\n", "\n", text)
        return re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"


def storage_to_markdown(xhtml: str) -> str:
    # CDATA holds code-macro bodies; HTMLParser would otherwise drop it as a declaration.
    xhtml = re.sub(r"<!\[CDATA\[(.*?)\]\]>", lambda m: _escape(m.group(1)), xhtml, flags=re.S)
    p = _Storage()
    p.feed(xhtml)
    p.close()
    return p.markdown()


def _escape(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ------------------------------------------------------------------ fetch ----
def page_id_from(ref: str) -> str:
    if ref.isdigit():
        return ref
    m = re.search(r"/pages/(\d+)", ref) or re.search(r"[?&]pageId=(\d+)", ref)
    if not m:
        sys.exit(f"cannot find a page id in {ref!r} — pass the numeric id")
    return m.group(1)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Refuse every redirect. urllib copies the Authorization header onto the
    redirected request, so following one could hand the credential to another
    host, or send it over plain HTTP. A moved page is an error to read, not to
    follow."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001, PLR0913
        raise urllib.error.HTTPError(req.full_url, code,
                                     f"refusing redirect to {newurl} with credentials attached", headers, fp)


_OPENER = urllib.request.build_opener(_NoRedirect)


def _get(url: str) -> dict:
    if not url.startswith("https://"):
        sys.exit(f"refusing to send credentials to a non-https URL: {url}")
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    if os.environ.get("CONFLUENCE_PAT"):
        req.add_header("Authorization", f"Bearer {os.environ['CONFLUENCE_PAT']}")
    else:
        user, token = os.environ.get("CONFLUENCE_EMAIL"), os.environ.get("CONFLUENCE_API_TOKEN")
        if not (user and token):
            sys.exit("set CONFLUENCE_EMAIL and CONFLUENCE_API_TOKEN (or CONFLUENCE_PAT) in the environment")
        req.add_header("Authorization", "Basic " + base64.b64encode(f"{user}:{token}".encode()).decode())
    with _OPENER.open(req, timeout=30) as resp:  # https only, redirects refused (above)
        return json.load(resp)


def fetch(base: str, page_id: str, api: str) -> dict:
    """{id, title, version, url, body} for one page."""
    base = base.rstrip("/")
    if api == "v2":
        d = _get(f"{base}/wiki/api/v2/pages/{page_id}?body-format=storage")
        return {"id": page_id, "title": d.get("title"), "version": (d.get("version") or {}).get("number"),
                "url": base + "/wiki" + ((d.get("_links") or {}).get("webui") or f"/pages/{page_id}"),
                "body": ((d.get("body") or {}).get("storage") or {}).get("value", "")}
    d = _get(f"{base}/rest/api/content/{page_id}?expand=body.storage,version")
    return {"id": page_id, "title": d.get("title"), "version": (d.get("version") or {}).get("number"),
            "url": base + ((d.get("_links") or {}).get("webui") or ""),
            "body": ((d.get("body") or {}).get("storage") or {}).get("value", "")}


def children(base: str, page_id: str, api: str) -> list[str]:
    base = base.rstrip("/")
    if api == "v2":
        d = _get(f"{base}/wiki/api/v2/pages/{page_id}/children?limit=250")
        return [str(c["id"]) for c in d.get("results", [])]
    d = _get(f"{base}/rest/api/content/{page_id}/child/page?limit=250")
    return [str(c["id"]) for c in d.get("results", [])]


def render(pages: list[dict]) -> str:
    root = pages[0]
    bodies = []
    for i, p in enumerate(pages):
        md = storage_to_markdown(p["body"])
        bodies.append(md if i == 0 else f"\n---\n\n# Child page: {p['title']} (id {p['id']}, v{p['version']})\n\n{md}")
    body = "".join(bodies)
    front = {
        "page_id": root["id"], "title": root["title"], "version": root["version"], "url": root["url"],
        "children": [{"id": p["id"], "title": p["title"], "version": p["version"]} for p in pages[1:]],
        "fetched_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
    }
    lines = ["---"] + [f"{k}: {json.dumps(v, ensure_ascii=False)}" for k, v in front.items()] + ["---", ""]
    return "\n".join(lines) + f"# {root['title']}\n\n" + body


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("page", nargs="?", help="page URL or numeric id")
    ap.add_argument("--from-file", type=Path, help="convert an exported storage/HTML file offline")
    ap.add_argument("--children", action="store_true", help="append direct child pages")
    ap.add_argument("--api", choices=["v2", "v1"], default="v2", help="v1 for Server / Data Center")
    ap.add_argument("--out", type=Path, help="write here instead of stdout")
    args = ap.parse_args(argv)

    if args.from_file:
        raw = args.from_file.read_text(encoding="utf-8")
        pages = [{"id": "unknown", "title": args.from_file.stem, "version": f"file-{args.from_file.name}",
                  "url": None, "body": raw}]
    elif args.page:
        base = os.environ.get("CONFLUENCE_BASE_URL")
        if not base or not base.startswith("https://"):
            sys.exit("set CONFLUENCE_BASE_URL to the site's https:// root")
        pid = page_id_from(args.page)
        pages = [fetch(base, pid, args.api)]
        if args.children:
            pages += [fetch(base, c, args.api) for c in children(base, pid, args.api)]
    else:
        ap.error("pass a page URL/id or --from-file")

    text = render(pages)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
        print(f"✓ {args.out} — {pages[0]['title']} v{pages[0]['version']}, {len(pages) - 1} child page(s)")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
