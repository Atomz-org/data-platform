# Commodities — what every sister's numbers mean

Stated once for the `commodity` family and copied into each sister's workspace
by `pf tool wren workspace`. It holds for every market this family lands in and
every exchange it reads. Edit it here and regenerate; never in a project.

## Prices
- A price is per one unit of measure (`unit_of_measure`: troy_oz, kg, 10 g,
  barrel, MMBtu, metric_ton, bale …) in one currency (`currency_code`). Two
  prices are comparable only when both match. Across commodities, compare
  returns, volatility, premiums or percentage moves, never price levels.
- A price is never summed, and never averaged across commodities. An average
  price is one commodity's average over its own days, the cube's measure, which
  divides a sum by its own count.
- "Latest price" is each commodity's own last trading day (`max(trade_date)`
  per commodity). Feeds and exchange holidays differ, so one global date is a
  stale answer for some commodities.

## Exchange contracts
- A commodity trades as several contracts, one per expiry. "The price of X"
  means its flagship or continuous series (`is_flagship`, the roll-up fact),
  never every contract averaged or summed.
- Contango means a later expiry is priced above the nearer one. Backwardation is
  the reverse. Roll yield is annualised, so read it as a rate, not a sum.
- Volume and open interest count lots, and a lot's size differs by contract
  (mini, micro, full). Add lots only within one contract. Across contracts, use
  turnover (money) or the lot-equivalent fact.

## Currencies and landed cost
- An FX rate is units of quote currency per one unit of base currency. A local
  landed price is the benchmark in USD times the rate, plus duty and charges.
  Convert before comparing a local price with a USD benchmark.
- Money is additive only within one currency. Turnover in one currency may be
  summed over days; totals across currencies are not an answer.

## Returns, volatility, indicators
- Percentages are stored as fractions: 0.15 means 15%.
- Daily returns compound. The average daily return is a rate, and a period's
  return is its first and last price, not a sum of daily returns.
- Volatilities (realised, Parkinson, Garman–Klass, Rogers–Satchell) are
  annualised rates: average them over days, never sum them. RSI, momentum and
  range position are bounded indicators: average them, never sum them.

## Scope
- One sister sees one market. A comparison across markets or exchanges is the
  roll-up project's question, never a join guessed here.
