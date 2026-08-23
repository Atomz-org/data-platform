"""LLM-backed agents. Deterministic evidence in, typed verdict out."""

from pf.agents.base import AGENTS, AgentConfig, NoCredentials, cached_prefix, call, have_credentials
from pf.agents.loops import (
    AnomalyReport,
    Diagnosis,
    FixPatch,
    MetricProposal,
    MetricProposals,
    assess_anomaly,
    draft_fix,
    propose_metrics,
    triage_failures,
)

__all__ = [
    "AGENTS",
    "AgentConfig",
    "AnomalyReport",
    "Diagnosis",
    "FixPatch",
    "MetricProposal",
    "MetricProposals",
    "NoCredentials",
    "assess_anomaly",
    "cached_prefix",
    "call",
    "draft_fix",
    "have_credentials",
    "propose_metrics",
    "triage_failures",
]
