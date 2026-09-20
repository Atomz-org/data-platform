# ADR-0001: US duty is the published rate, with origin left out

**Status:** accepted · 2026-09-20

## Context

The conformed landed price needs one `effective_duty_rate` per commodity per
day. The United States has no such number. Duty on a shipment depends on its
HTSUS line, its country of origin (MFN, USMCA, the IEEPA reciprocal schedule
by country, antidumping and countervailing orders), whether it lands inside a
tariff-rate quota, and — for metals and lumber — a Section 232 proclamation.
Several of these are specific duties in cents per kilogram, not percentages.

## Decision

`import_duties` records, per commodity and dated interval, the rate a buyer of
the benchmark grade faces **without knowing the origin**, and says in
`duty_basis` exactly which simplification produced it:

- **Section 232** rates are taken from their proclamations and dated from
  their effective days (aluminium 10% → 25% → 50%; steel 25% → 50%; softwood
  lumber 10%). Country exemptions and quotas that applied before March 2025
  are not modelled. `confirmed_from` is the effective date.
- **MFN ad valorem** rates are taken as printed in the HTSUS.
- **Specific duties** (cents/kg, cents/barrel, cents/litre) are converted to
  a fraction at a stated benchmark price when the result is above about 1%
  (rice, wheat, soybean meal, orange juice) and recorded as nil below it
  (crude oil, corn, live cattle). The reference price is in `duty_basis`.
- **Tariff-rate quotas** carry the in-quota rate; the over-quota rate (raw
  sugar 33.87¢/kg, upland cotton 31.4¢/kg) is named and not applied.
- **IEEPA reciprocal tariffs, antidumping and countervailing duties** are not
  applied, because they depend on origin. Commodities whose landed price could
  be materially understated for some origins have no `confirmed_from`, so
  `is_duty_rate_confirmed` is false on every row and the board says so.
- The refined-copper benchmark is outside Section 232 copper (cathode, ore,
  concentrate and scrap were excluded); it carries the 1% MFN rate.
- Nothing is recorded as prohibited. The suspension of Mexican live-cattle
  imports is an animal-health measure, not a customs one.

## Consequences

- For a US buyer the landed price is **import parity**: with `usd_fx_rate` = 1
  it is the benchmark grossed up by the rate above, so the number differs from
  the benchmark only for the dutiable commodities. That is the intended
  reading — "what does the tariff add" — not a customs calculator.
- A desk that knows the origin adds a dated row with the origin-specific rate
  and closes the interval of the generic one, exactly as in ADR-0001 of
  commodity-india; the generic row is never edited.
- Rates were taken as of September 2026 from the proclamations and HTSUS
  headings named in `duty_basis`. Check the current HTSUS and CBP guidance
  before quoting a landed price to anyone.
