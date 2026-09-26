-- MCX's option `Value` is notional ((strike + premium) × quantity), so the
-- premium derived from it must sit between zero and that notional. A row here
-- means Value was read as something else — the mistake that once reported
-- option premium at forty times its size. A few rupees of rounding is allowed.
select chain_day_id, premium_turnover_inr, notional_turnover_inr
from {{ ref('int_mcx__options_chain_daily') }}
where premium_turnover_inr < -0.001 * notional_turnover_inr - 100
   or premium_turnover_inr > notional_turnover_inr
