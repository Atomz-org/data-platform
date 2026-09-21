---
title: Market Comparison
---

Where is each commodity cheapest to land, and what does every other market pay over
that? Every number here stands on the benchmark's footing — USD per the commodity's own
quote unit, with each market's FX undone at the rate it applied — so the difference
between two markets is duty and timing, nothing else.

```sql markets
select
    market_code,
    market_name,
    currency_code,
    is_reporting,
    latest_price_date,
    commodities_priced
from commodity_rollup.dim_markets
order by market_code
```

<DataTable data={markets} rows=10>
    <Column id=market_code title='Market'/>
    <Column id=market_name title='Name'/>
    <Column id=currency_code title='Reports in'/>
    <Column id=is_reporting title='Reporting'/>
    <Column id=latest_price_date title='Latest price'/>
    <Column id=commodities_priced title='Commodities' fmt=num0/>
</DataTable>

## Import-parity premium by market

The premium is landed over benchmark, minus one. For a duty-free commodity in a USD
market it is zero by construction; for aluminium in the United States it is the
Section 232 tariff. A bar that is not a round duty rate is FX timing: the fix was
carried over a holiday.

```sql premium
select
    commodity_name,
    market_code,
    import_parity_premium_pct
from commodity_rollup.rpt_market_comparison_board
where not is_import_prohibited and import_parity_premium_pct is not null
order by commodity_name, market_code
```

<BarChart
    data={premium}
    x=commodity_name
    y=import_parity_premium_pct
    series=market_code
    type=grouped
    swapXY=true
    title='What landing adds over the benchmark, by market'
    xFmt=pct1
/>

## Cheapest market and the spread to it

```sql spreads
select
    commodity_name,
    category,
    market_code,
    currency_code,
    price_date,
    benchmark_price_usd,
    quote_unit,
    landed_price_local,
    market_unit,
    landed_price_usd_per_quote_unit,
    cheapest_market_code,
    is_cheapest_market,
    spread_to_cheapest_pct,
    effective_duty_rate,
    is_duty_rate_confirmed,
    price_age_days,
    is_stale
from commodity_rollup.rpt_market_comparison_board
where not is_import_prohibited
order by commodity_name, spread_to_cheapest_pct desc nulls last
```

<DataTable data={spreads} rows=20 search=true>
    <Column id=commodity_name title='Commodity'/>
    <Column id=market_code title='Market'/>
    <Column id=price_date title='Priced'/>
    <Column id=price_age_days title='Age (d)' fmt=num0 contentType=colorscale/>
    <Column id=benchmark_price_usd title='Benchmark (USD)' fmt=num2/>
    <Column id=quote_unit title='Per'/>
    <Column id=landed_price_local title='Landed (local)' fmt=num2/>
    <Column id=currency_code title='Ccy'/>
    <Column id=market_unit title='Per'/>
    <Column id=landed_price_usd_per_quote_unit title='Landed (USD / quote unit)' fmt=num2/>
    <Column id=cheapest_market_code title='Cheapest'/>
    <Column id=spread_to_cheapest_pct title='Over cheapest' fmt=pct1 contentType=delta downIsGood=true/>
    <Column id=effective_duty_rate title='Duty' fmt=pct1/>
    <Column id=is_duty_rate_confirmed title='Duty confirmed'/>
</DataTable>

---

_Source: `rpt_market_comparison_board`, one row per commodity per market at its latest
price date. A market missing from a row has not priced that commodity; a market missing
from the table above has not seeded. The comparison logic lives in
`fct_landed_prices_daily` and `fct_market_spreads_daily`; this page selects and formats._
