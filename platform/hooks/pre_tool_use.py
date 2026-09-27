#!/usr/bin/env python3
"""Claude Code PreToolUse hook — stages 01 and 02 of the provenance chain.

Reads the tool call on stdin. Writes INTENT (what the agent proposed), consults
the policy gate, then writes DECISION (what the gate said) — in that order,
before the tool runs. `post_tool_use.py` closes the action with EXECUTION.

Denies writes to generated artefacts, secrets and shared platform infra; for
models and sources it prints the blast radius as feedback so the decision is
informed rather than blocked.

Recording is deliberately ordered so the record cannot flatter the outcome:
INTENT is written before the gate is consulted, so a denied action still leaves
evidence of what was attempted. A gate that only logs its refusals can prove it
said no; it cannot prove it was ever asked.

exit 0 = allow (stdout is shown to the agent)
exit 2 = block (stderr is shown to the agent)

The logic lives in `pf.agenthook`, shared with every other harness through
`agent_hook.py`; this file is Claude Code's entry point to it, kept by name
because settings, docs and the AIR controls cite it.
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

if __name__ == "__main__":
    sys.argv = [str(Path(__file__).with_name("agent_hook.py")), "claude", "pre"]
    runpy.run_path(sys.argv[0], run_name="__main__")
