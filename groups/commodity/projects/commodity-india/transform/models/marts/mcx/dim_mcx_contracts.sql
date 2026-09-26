-- Grain: one MCX futures contract or option expiry chain. The expiry calendar:
-- what is listed, what it is written on, how long it has left, and whether it
-- traded in the latest session.
with contracts as (
    select * from {{ ref('stg_mcx__contract_master') }}
),

products as (
    select * from {{ ref('mcx_products') }}
),

latest as (
    select max(cast(traded_at as date)) as latest_trade_date
    from {{ ref('stg_mcx__futures_bhavcopy') }}
)

select
    c.contract_id,
    c.contract_code,
    p.mcx_commodity,
    p.commodity_id,
    p.contract_name,
    p.segment,
    p.is_flagship,
    c.instrument_type,
    case c.instrument_type when 'futcom' then 'future' when 'optfut' then 'option_chain' end as contract_kind,
    cast(c.expiry_date as date)                                         as expiry_date,
    'MCX'                                                                as exchange,
    cast(c.expiry_date as date) >= l.latest_trade_date                  as is_open,
    {{ sf_datediff('day', 'l.latest_trade_date', 'cast(c.expiry_date as date)') }} as days_to_expiry,
    c.is_traded_today,
    p.lot_size,
    p.lot_unit,
    p.quote_size,
    p.quote_unit
from contracts as c
inner join products as p on p.contract_code = c.contract_code
cross join latest as l
