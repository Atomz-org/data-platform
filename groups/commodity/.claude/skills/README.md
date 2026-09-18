# commodity group skills

Skills specific to this group's business, shared by every sister project.
Infra skills come from `platform/toolkits`; do not duplicate them here.

Put a skill here when it encodes commodity's domain knowledge (a reconciliation
procedure, a regulatory workflow, a naming rule the ontology cannot express).

| Skill | Use it when |
|---|---|
| `price-arithmetic` | converting a price: minor currency, unit, FX, duty, in that order, once each |
| `add-a-commodity` | adding a tracked commodity: the group half and the sister half |
| `price-feed-triage` | a price load is stale or empty: classify calendar, feed, symbol, cursor or contract before fixing |

Loaded through the group marketplace (`../../.claude-plugin/marketplace.json`).
`../.claude-plugin/plugin.json` beside this directory is what makes it a plugin;
without it the marketplace entry loads nothing.
