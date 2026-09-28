# AI governance & DORA — globex-eu

Every agent output that becomes a metric or a semantic model here goes through
the governance engine, and every outcome is a hash-linked record in the
repository's provenance chain. This project is governed by the platform floor
plus `groups/globex/aidf.yaml` plus `governance/aidf.yaml` in this directory,
each layer tightening the one before.

## Runtime governance

```
pf govern check globex globex-eu            what governs this entity, and the breaker's state
pf govern schema mart_metric                   the JSON an agent must produce
pf govern prompt globex globex-eu <mart> <metric>   the dispatch prompt, with this mart's catalogue
pf govern evaluate globex globex-eu --payload p.json --role metric-gap-harvester
pf govern breaker globex globex-eu [--reset --reason "..."]
```

An evaluation ends in one of four states, each written to the chain:

| status | decision / execution | meaning |
|---|---|---|
| `PASS` | allow / ok | every check holds; the record was written under `governance/metrics/` |
| `REJECT` | deny / blocked | a check failed; the findings are in the record, the payload is not |
| `ESCALATED` | hold / blocked | elevated target; `pf provenance approve <id>` then resubmit `--approved` |
| `CIRCUIT_BROKEN` | deny / blocked | too many consecutive rejections; a person resets with a reason |

The MCP tools `govern_metric` and `govern_prompt` are the same engine for any
harness that speaks MCP.

## DORA evidence

```
pf dora matrix                       which article each check evidences
pf dora audit globex globex-eu  run what can run, judge every check, write governance/dora/matrix.md
pf dora audit globex globex-eu --ocsf findings.ocsf.json --vulns trivy.json   ingest scans run elsewhere
```

`governance/dora/` is generated and gitignored; CI archives it and the chain
records its SHA-256. A check the audit could not run here reads `unverified`
and is never counted as a pass. `docs/AIDF.md` at the repository root is the
full reference, including the statutory mapping and the supply-chain policy.
