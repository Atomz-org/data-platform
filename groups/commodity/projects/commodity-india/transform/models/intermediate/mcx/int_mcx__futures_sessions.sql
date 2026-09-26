-- Grain: one MCX futures contract per trading day. The staged bhavcopy made
-- readable to a desk: which expiry a row is (near, next, far), what one lot is
-- worth, how open interest moved, and which of MCX's numbers are real trades.
--
-- India-only and market-local (`intermediate/mcx/` is exempt from the family's
-- conformance comparison; see the group test). No currency or unit conversion
-- happens: MCX quotes ₹ per the contract's quote basis and every price here
-- stays in it. Notional is a restatement, close × quote bases per lot, not a
-- conversion (price-arithmetic skill).
with sessions as (
    select * from {{ ref('stg_mcx__futures_bhavcopy') }}
),

products as (
    select * from {{ ref('mcx_products') }}
),

typed as (
    select
        s.session_id,
        s.contract_id,
        s.contract_code,
        p.mcx_commodity,
        p.commodity_id,
        p.contract_name,
        p.segment,
        p.is_flagship,
        p.quote_size,
        p.quote_unit,
        p.lot_size,
        p.lot_unit,
        p.quote_units_per_lot,
        p.is_spec_verified,
        cast(s.traded_at as date)                                   as trade_date,
        cast(s.expiry_date as date)                                 as expiry_date,
        s.volume_lots,
        s.open_interest_lots,
        s.traded_quantity,
        s.quantity_unit,
        s.turnover_lakhs,
        -- MCX prints 0 for open, high and low on a day a contract did not trade,
        -- and carries the previous settlement as its close. A zero is "no trade",
        -- never a price: left in, it drags every range and ATR to the floor.
        case when s.volume_lots > 0 and s.open_price > 0 then s.open_price end as open_price,
        case when s.volume_lots > 0 and s.high_price > 0 then s.high_price end as high_price,
        case when s.volume_lots > 0 and s.low_price  > 0 then s.low_price  end as low_price,
        s.close_price,
        nullif(s.previous_close_price, 0)                           as previous_close_price,
        s.volume_lots > 0                                           as is_traded
    from sessions as s
    inner join products as p on p.contract_code = s.contract_code
),

ranked as (
    select
        *,
        {{ sf_datediff('day', 'trade_date', 'expiry_date') }}      as days_to_expiry,
        -- Near = 1, next = 2, far = 3, among the expiries still open that day.
        row_number() over (
            partition by contract_code, trade_date order by expiry_date
        )                                                           as expiry_rank,
        lag(open_interest_lots) over (
            partition by contract_id order by trade_date
        )                                                           as prev_open_interest_lots
    from typed
    where expiry_date >= trade_date
)

select
    session_id,
    contract_id,
    contract_code,
    mcx_commodity,
    commodity_id,
    contract_name,
    segment,
    is_flagship,
    trade_date,
    expiry_date,
    days_to_expiry,
    expiry_rank,
    case expiry_rank when 1 then 'near' when 2 then 'next' when 3 then 'far' else 'deferred' end
                                                                    as expiry_bucket,
    quote_size,
    quote_unit,
    lot_size,
    lot_unit,
    quote_units_per_lot,
    is_spec_verified,
    is_traded,
    open_price,
    high_price,
    low_price,
    close_price,
    previous_close_price,
    close_price - previous_close_price                              as price_change,
    {{ sf_safe_divide('close_price - previous_close_price', 'previous_close_price') }}
                                                                    as price_change_pct,
    volume_lots,
    open_interest_lots,
    open_interest_lots - prev_open_interest_lots                    as open_interest_change_lots,
    traded_quantity,
    quantity_unit,
    turnover_lakhs,
    turnover_lakhs * 100000                                         as turnover_inr,
    close_price * quote_units_per_lot                               as notional_per_lot_inr,
    open_interest_lots * close_price * quote_units_per_lot          as open_interest_value_inr,
    -- What MCX's own turnover says one lot was worth at the average traded
    -- price, as quote bases per lot. The seed's basis is checked against it.
    case when volume_lots > 0 and turnover_lakhs > 0 and close_price > 0
         then turnover_lakhs * 100000 / volume_lots / close_price end
                                                                    as implied_quote_units_per_lot
from ranked
