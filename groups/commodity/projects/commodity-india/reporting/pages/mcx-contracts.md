---
title: MCX Contract Board
---

What one lot of each tracked MCX contract is worth in rupees at the latest benchmark, and
which of those numbers is standing on a stale price. Sizing a position from a stale lot
value is the specific mistake this page exists to prevent.

```sql contract_summary
select
    count(*)                             as contracts,
    count(*) filter (where is_stale)     as stale_contracts,
    max(price_date)                      as latest_price_date
from commodity_india.rpt_mcx_contract_board
```

<Grid cols=3>

<BigValue data={contract_summary} value=contracts title='Contracts tracked' fmt=num0/>
<BigValue data={contract_summary} value=stale_contracts title='On a stale benchmark' fmt=num0/>
<BigValue data={contract_summary} value=latest_price_date title='Latest price date'/>

</Grid>

## Lot value

One bar per contract: lot size multiplied by the quote equivalent in INR. Values span
three orders of magnitude, from a one-gram Gold Petal to a thirty-kilo Silver lot, so
read the axis rather than the bar length alone.

```sql lot_value
select
    contract_name,
    lot_value_inr,
    is_stale
from commodity_india.rpt_mcx_contract_board
order by lot_value_inr desc
```

<BarChart
    data={lot_value}
    x=contract_name
    y=lot_value_inr
    swapXY=true
    title='INR per lot, at the latest benchmark'
    xFmt=num0
/>

## The board

```sql contracts
select
    contract_code,
    contract_name,
    commodity_id,
    exchange,
    price_date,
    price_basis,
    quote_size,
    quote_unit,
    quote_equivalent_inr,
    lot_size,
    lot_unit,
    lot_value_inr,
    price_age_days,
    is_stale,
    is_duty_rate_confirmed
from commodity_india.rpt_mcx_contract_board
order by is_stale desc, lot_value_inr desc
```

<DataTable data={contracts} rows=12>
    <Column id=contract_code title='Code'/>
    <Column id=contract_name title='Contract'/>
    <Column id=price_date title='Priced'/>
    <Column id=price_age_days title='Age (d)' fmt=num0 contentType=colorscale/>
    <Column id=quote_equivalent_inr title='Per quote unit (INR)' fmt=num2/>
    <Column id=quote_unit title='Quote unit'/>
    <Column id=lot_size title='Lot' fmt=num0/>
    <Column id=lot_unit title='Lot unit'/>
    <Column id=lot_value_inr title='Lot value (INR)' fmt=num0/>
    <Column id=is_duty_rate_confirmed title='Duty confirmed'/>
</DataTable>

---

_Source: `rpt_mcx_contract_board`, one row per contract at its latest price date. Zinc has
no free live feed; ZINC and ZINCMINI carry the last indicative LME level and are flagged
stale until `indicative_prices` is refreshed._
