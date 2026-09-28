"""JetBrains Junie (CLI) — `AGENTS.md`, and hooks passed at start.

    .junie/config.json   SessionStart, PreToolUse (Bash, Edit, Write, Read), Stop
                         → `agent_hook.py junie <event>`

Junie ignores hooks in a project's config unless it is started with
`--config-location` on this file, which `bin/agent-here junie` passes. It has
no post-tool event, so it is gated but writes no provenance — an INTENT
nothing closes is a dangling action — and advice rides on the pre answer.
Its tool names are Claude's, so its dialect is Claude's with Junie's output
keys.
"""

from __future__ import annotations

import json

from pf.agenthook import BASH, EDIT, READ, WRITE
from pf.harness import SKILLS_CELL, Harness, claude_style_hooks, json_text
from pf.harness_adapters import Adapter, claude_parse, exit2, generic_ok
from pf.harnesses.base import Ctx, Spec


def _render(ctx: Ctx) -> dict[str, str]:
    return {".junie/config.json": json_text(claude_style_hooks("junie", "Bash|Edit|Write|Read", post=False))}


SPEC = Spec(
    key="junie",
    label="Junie",
    order=60,
    rows=(
        Harness(
            "Junie CLI",
            "`AGENTS.md`",
            "none — `pf mcp` by hand",
            "hook — via `bin/agent-here junie` only",
            "pre-commit",
            "none — no post-tool event",
            "injected on turn one",
            "SessionStart hook",
            SKILLS_CELL,
            "none",
            ".junie/config.json",
            "junie",
        ),
    ),
    render=_render,
    owner="Junie CLI",
    adapter=Adapter(
        parse=claude_parse("junie"),
        deny=exit2,
        allow=lambda v: (json.dumps({"decision": "allow", "additionalContext": v.message}) if v.message else "", "", 0),
        ask=lambda v: (json.dumps({"decision": "ask", "reason": v.message}), "", 0),
        context=lambda ev, text: (json.dumps({"additionalContext": text}) if text else "", "", 0),
        ok=generic_ok,
    ),
    tools={"Edit": EDIT, "Write": WRITE, "Bash": BASH, "Read": READ},
    no_post=True,
    caveats=(
        "- **Junie** ignores project hooks unless started with `--config-location`, which",
        "  is what `bin/agent-here junie` passes. It has no post-tool event, so it writes",
        "  no provenance: an INTENT nothing closes would be a dangling action.",
    ),
    launch="junie",
)
