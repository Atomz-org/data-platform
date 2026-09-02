"""Loop engineering for the data platform.

Building blocks adapted from loop-engineering (vendor/loop-engineering):
durable state, path gate, token budget, circuit breaker, ledger, readiness score.
The loops themselves are data-platform loops, not software-delivery ones.
"""

from pf.loops.audit import audit, recommended_level
from pf.loops.gate import GateResult, check_path, check_paths, nodes_for, project_for
from pf.loops.registry import BODIES, SPECS, all_bodies, all_loops, all_specs
from pf.loops.runner import CircuitBreaker, Ledger, LoopRun, LoopSpec, run_loop, update_state

__all__ = [
    "BODIES",
    "SPECS",
    "CircuitBreaker",
    "GateResult",
    "Ledger",
    "LoopRun",
    "LoopSpec",
    "all_bodies",
    "all_loops",
    "all_specs",
    "audit",
    "check_path",
    "check_paths",
    "nodes_for",
    "project_for",
    "recommended_level",
    "run_loop",
    "update_state",
]
