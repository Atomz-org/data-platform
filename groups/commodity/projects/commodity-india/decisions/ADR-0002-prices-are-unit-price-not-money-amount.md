# ADR-0002: Prices carry the `unit_price` role, not `money_amount`

**Status:** accepted · 2026-09-16

## Context

The platform ontology's only monetary role is `money_amount`. Two things come
with it, and both are wrong for a benchmark price:

- **Staging rounds it to two decimals** (`clean_money` casts to
  `decimal(18, 2)`). NYMEX natural gas settles in tenths of a cent: $2.889 would
  land as $2.89, and the error is carried through every unit and FX conversion
  downstream.
- **It is treated as additive.** `monitors_for` attaches a `sum_drift` monitor,
  and the reporting layer sums it. A sum of gold and copper prices is not a
  number anyone should look at.

## Decision

The `commodity` group extension (`groups/commodity/ontology/extension.yaml`)
declares `unit_price` (plus `unit_of_measure`, `exchange_rate`,
`rate_fraction`). `pf_clean` passes unknown roles through untouched, so staging
keeps full precision and sign. A price still carries a sibling `currency_code`.

Currency conversion that `money_amount` would have implied is done explicitly:
`to_major_currency` (cents → dollars) in `int_commodity_prices__usd`, and the
USD/INR join in the landed-price mart.

## Consequences

- No `sum_drift` monitor on prices. Freshness and row-count monitors still apply.
- Downstream tools that key on `money_amount` (currency normalisation) do not
  recognise these columns. The MDL projection types them from the group role's
  `datatype` (DECIMAL) and tags them `pf.role: unit_price`; unannotated derived
  columns such as `prev_close_price` keep their physical `DOUBLE`.
- The role belongs to the group, not the platform. Promoting it is a separate,
  deliberate platform change if another group needs it.
