#!/usr/bin/env python3
"""Claude Code PostToolUse hook — stage 03 of the provenance chain.

Closes the action `pre_tool_use.py` opened: writes EXECUTION with what actually
happened, linked to the same `action_id` by the correlation key both hooks
compute from the tool call.

This hook never blocks. PostToolUse runs after the tool has already changed the
world, so a non-zero exit here cannot prevent anything — it would only inject a
misleading error into the transcript for work that succeeded. Everything is
best-effort and silent on failure; `pf provenance verify` is what reports the
gaps, and an action left without an EXECUTION is visible there as dangling.

exit 0 always.

The logic lives in `pf.agenthook`, shared with every other harness through
`agent_hook.py`; this file is Claude Code's entry point to it, kept by name
because settings, docs and the AIR controls cite it.
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

if __name__ == "__main__":
    sys.argv = [str(Path(__file__).with_name("agent_hook.py")), "claude", "post"]
    runpy.run_path(sys.argv[0], run_name="__main__")
