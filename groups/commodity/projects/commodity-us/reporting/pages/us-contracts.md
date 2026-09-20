---
title: US Contract Board
---

What one lot of each tracked CME Group and ICE contract is worth at import parity — the
latest benchmark grossed up by the duty a US buyer would face — and which of those numbers
is standing on a stale price. For a duty-free contract this is the contract's own notional;
for aluminium and steel it is what the Section 232 tariff adds to it.

```sql contract_summary
select
    count(*)                             as contracts,
    count(*) filter (where is_stale)     as stale_contracts,
    max(price_date)                      as latest_price_date
from commodity_us.rpt_us_contract_board
```

<Grid cols=3>

<BigValue data={contract_summary} value=contracts title='Contracts tracked' fmt=num0/>
<BigValue data={contract_summary} value=stale_contracts title='On a stale benchmark' fmt=num0/>
<BigValue data={contract_summary} value=latest_price_date title='Latest price date'/>

</Grid>

## Lot value

One bar per contract: lot size multiplied by the quote equivalent in USD. Values span
orders of magnitude, from a 10-ounce Micro Gold to a 1,000-barrel crude lot, so read the
axis rather than the bar length alone.

```sql lot_value
select
    contract_name,
    exchange,
    lot_value_usd,
    is_stale
from commodity_us.rpt_us_contract_board
order by lot_value_usd desc
```

<BarChart
    data={lot_value}
    x=contract_name
    y=lot_value_usd
    swapXY=true
    title='USD per lot, at import parity on the latest benchmark'
    xFmt=num0
/>

## The board

```sql contracts
select
    contract_code,
    exchange,
    contract_name,
    commodity_id,
    price_date,
    price_basis,
    effective_duty_rate,
    quote_size,
    quote_unit,
    quote_equivalent_usd,
    lot_size,
    lot_unit,
    lot_value_usd,
    price_age_days,
    is_stale,
    is_duty_rate_confirmed
from commodity_us.rpt_us_contract_board
order by is_stale desc, lot_value_usd desc
```

<DataTable data={contracts} rows=26>
    <Column id=contract_code title='Code'/>
    <Column id=exchange title='Exchange'/>
    <Column id=contract_name title='Contract'/>
    <Column id=price_date title='Priced'/>
    <Column id=price_age_days title='Age (d)' fmt=num0 contentType=colorscale/>
    <Column id=effective_duty_rate title='Duty' fmt=pct1/>
    <Column id=quote_equivalent_usd title='Per quote unit (USD)' fmt=num2/>
    <Column id=quote_unit title='Quote unit'/>
    <Column id=lot_size title='Lot' fmt=num0/>
    <Column id=lot_unit title='Lot unit'/>
    <Column id=lot_value_usd title='Lot value (USD)' fmt=num0/>
    <Column id=is_duty_rate_confirmed title='Duty confirmed'/>
</DataTable>

---

_Source: `rpt_us_contract_board`, one row per contract at its latest price date. Only
contracts with a live feed appear here; the LME metals and other feedless commodities have
no US contract in `us_contract_lots`. Duty confirmation follows ADR-0001: a row without it
carries a rate whose origin-dependent components are not modelled._
