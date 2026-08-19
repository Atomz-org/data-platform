"""AIR — the risk taxonomy and control catalogue, and our coverage of it.

The fourth side of this platform's governance question. `pf.provenance` is
runtime evidence (what an agent did, hash-linked and anchored),
`vendor/asqav-compliance` is static analysis (whether a control exists in the
source), `vendor/public-sector-ai-playbook` is the artefact a regulator is
handed. None of the three says *which controls there are*, or which regulation
each one discharges. That referent is the vendored FINOS AI Governance Framework,
and this package reads it.

Named `air` for upstream's own id scheme (`AIR-SEC-24`, `AIR-DET-21`) and site.
Not `governance` — `pf.governance` is the ontology *edit* store, a different
thing that was here first.

Two rules carry the design:

**Coverage is derived, never recorded.** A control is `pass` because a policy
claims it and the artefact that policy names resolves on disk right now. Nothing
writes a verdict down, because a recorded pass survives the change that
invalidated it. Same rule as `pf.onboard.ladder`, same vocabulary (`pf.checks`).

**Only `fail` blocks.** A control that is claimed and demonstrably not enforced
fails a declared baseline. A control whose artefact exists but has never run is
`unexercised`, reported loudly, and exits zero.
"""

from pf.air.catalogue import (
    Catalogue,
    Control,
    CorpusError,
    NotVendored,
    Reference,
    Regime,
    Risk,
    absent_reason,
    available,
    load,
)
from pf.air.coverage import Claim, ControlVerdict, Coverage, assess
from pf.air.register import (
    NO_ATTRIBUTION,
    Acceptance,
    AirConfig,
    GateResult,
    RegisterError,
    gate,
    load_config,
    render_register,
    validate,
    write_register,
)
from pf.air.sources import (
    BUILTIN,
    CatalogueSource,
    Frontmatter,
    InvalidSource,
    Layout,
    all_sources,
    available_sources,
)
from pf.air.verify import Finding, VerifyReport, verify

__all__ = [
    "BUILTIN", "NO_ATTRIBUTION",
    "Acceptance", "AirConfig", "Catalogue", "CatalogueSource", "Claim", "Control",
    "ControlVerdict", "CorpusError", "Coverage", "Finding", "Frontmatter",
    "GateResult", "InvalidSource", "Layout", "NotVendored", "Reference", "Regime",
    "RegisterError", "Risk", "VerifyReport",
    "absent_reason", "all_sources", "assess", "available", "available_sources",
    "gate", "load", "load_config", "render_register", "validate", "verify",
    "write_register",
]
