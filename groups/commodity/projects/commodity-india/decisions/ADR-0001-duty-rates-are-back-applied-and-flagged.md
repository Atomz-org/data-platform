# ADR-0001: Duty rates are back-applied to history, and flagged

**Status:** accepted · 2026-09-16

## Context

The landed price needs India's customs duty on every date in a five-year price
history. The only verified source is the June 2026 schedule the upstream tracker
(MrChartist/commodity-price-tracker) publishes, including the May 2026 bullion
hike to 15% and the 2026 cotton exemption window. Earlier notifications — for
example gold's 6% rate from the July 2024 budget — are known to exist but have
not been sourced with exact effective dates.

Three options were considered:

1. Price history only from the verification date. Correct, but discards five
   years of landed history, and every trend metric starts in June 2026.
2. Invent historical rates from memory. Rejected: a plausible wrong rate is worse
   than an obviously missing one.
3. Apply today's rate to earlier dates, and say so on every row.

## Decision

Option 3. `import_duties` has one base row per commodity valid from
`1900-01-01`, or, where the notifications are dated (cotton), a chain of dated
rows that starts there.
`confirmed_from` records the first date a row is known to be in force; a
back-applied row leaves it at the verification date, and a row whose whole
interval is unverified leaves it empty.

`fct_india_landed_prices_daily.is_duty_rate_confirmed` is true only on or after
`confirmed_from`. Anything that reports historical landed prices filters or
labels on it.

## Consequences

- Landed prices before June 2026 are "today's duty on that day's benchmark", not
  the historical landed cost. For gold that overstates pre-May-2026 duty.
- Sourcing a historical notification moves the base row's `valid_from`
  forward to the notification date and adds a dated row covering the period
  before it. The rates on an existing row are never edited; only its interval
  closes. The overlap test (`assert_tariff_intervals_do_not_overlap`) keeps
  that honest.
- `steel_hrc` carries the published 19.75% total. Its safeguard share
  (`other_levy_rate`, 11.5%) is the residual after BCD and SWS, not a separately
  sourced figure.
