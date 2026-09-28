"""DORA (Regulation (EU) 2022/2554) evidence for one entity.

    mapping   the statutory matrix: article -> checks -> how each is evidenced
    ocsf      Prowler's OCSF findings, normalised
    sbom      the dependency bill of materials and the RTS Art. 10 patch policy
    audit     runs what can run, ingests what was run elsewhere, and writes the
              evidence matrix — then records that it did to the provenance chain

Nothing here is per company. An entity says which cloud it is on, who owns its
framework and which articles do not apply to it (with a reason); the matrix,
the checks and the thresholds are the platform's, tightened per entity and
never loosened.
"""

from pf.aidf.dora.audit import AuditReport, run_audit
from pf.aidf.dora.mapping import Article, Check, load_mapping

__all__ = ["Article", "AuditReport", "Check", "load_mapping", "run_audit"]
