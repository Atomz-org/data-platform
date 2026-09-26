-- Grain: one MCX futures contract per trading day — every expiry, not only the
-- active one. The fact behind a term-structure chart and an expiry-by-expiry
-- open-interest table. Prices are ₹ per the contract's quote basis
-- (`quote_size` `quote_unit`): never sum them, never compare two codes' prices
-- without their quote basis (GOLD is per 10 g, GOLDPETAL per 1 g).
select
    s.session_id,
    s.contract_id,
    s.contract_code,
    s.mcx_commodity,
    s.commodity_id,
    s.contract_name,
    s.segment,
    s.is_flagship,
    s.trade_date,
    s.expiry_date,
    s.days_to_expiry,
    s.expiry_rank,
    s.expiry_bucket,
    s.quote_size,
    s.quote_unit,
    s.lot_size,
    s.lot_unit,
    s.quote_units_per_lot,
    s.is_traded,
    s.open_price,
    s.high_price,
    s.low_price,
    s.close_price,
    s.previous_close_price,
    s.price_change,
    s.price_change_pct,
    s.volume_lots,
    s.open_interest_lots,
    s.open_interest_change_lots,
    s.turnover_inr,
    s.notional_per_lot_inr,
    s.open_interest_value_inr,
    s.implied_quote_units_per_lot,
    s.is_spec_verified,
    {{ mcx_oi_buildup('s.price_change', 's.open_interest_change_lots') }} as oi_buildup,
    -- Volume ÷ open interest: above ~1 the day was churn (intraday traders
    -- turning over), well below it positions were held.
    {{ sf_safe_divide('s.volume_lots', 's.open_interest_lots') }}         as volume_to_oi_ratio
from {{ ref('int_mcx__futures_sessions') }} as s
