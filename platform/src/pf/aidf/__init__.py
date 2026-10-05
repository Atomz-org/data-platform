"""AI governance & DORA compliance framework (AIDF) — `pf govern`, `pf dora`.

Two pillars over one entity model, reaching every project through the `aidf`
capability and the platform floor in `data/defaults.yaml`:

    runtime governance   schemas, validators, gate, breaker, engine
                         an agent's output passes the contract, the SQL AST
                         check, the PII scrub and the path gate, and every
                         outcome is a hash-linked record in provenance/

    DORA evidence        dora/mapping, dora/ocsf, dora/sbom, dora/audit
                         Regulation (EU) 2022/2554 articles evidenced from
                         Prowler, Trivy, the provenance chain and the
                         repository, into a matrix the chain vouches for

docs/AIDF.md is the reference. Nothing here knows a company.
"""

from pf.aidf.config import AidfConfig, AidfConfigError, AidfRelaxation, load
from pf.aidf.engine import ActionGatePolicyViolation, BudgetExceeded, GovernanceEngine, Outcome
from pf.aidf.schemas import (
    AggregationType,
    GovernanceStatus,
    MartMetricContract,
    MetricStatus,
    SemanticModelContract,
)
from pf.aidf.validators import Finding, PiiScrubber, SqlAstValidator, Verdict

__all__ = [
    "ActionGatePolicyViolation",
    "AggregationType",
    "AidfConfig",
    "AidfConfigError",
    "AidfRelaxation",
    "BudgetExceeded",
    "Finding",
    "GovernanceEngine",
    "GovernanceStatus",
    "MartMetricContract",
    "MetricStatus",
    "Outcome",
    "PiiScrubber",
    "SemanticModelContract",
    "SqlAstValidator",
    "Verdict",
    "load",
]
