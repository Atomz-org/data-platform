-- source extract for fct_mcx_options_daily (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    chain_day_id,
    contract_id,
    trade_date,
    mcx_commodity,
    put_call_ratio_oi,
    max_pain_strike,
    premium_turnover_inr,
    contract_code,
    commodity_id,
    is_flagship,
    expiry_date,
    days_to_expiry,
    expiry_rank,
    is_latest,
    strikes_listed,
    call_open_interest_lots,
    put_open_interest_lots,
    call_volume_lots,
    put_volume_lots,
    notional_turnover_inr,
    put_call_ratio_volume,
    positioning,
    call_wall_strike,
    put_wall_strike,
    underlying_expiry_date,
    underlying_close_price,
    max_pain_distance_pct,
    call_wall_distance_pct,
    put_wall_distance_pct
from main_marts.fct_mcx_options_daily
