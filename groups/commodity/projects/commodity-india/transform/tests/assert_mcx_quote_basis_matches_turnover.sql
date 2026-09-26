-- MCX's turnover says what a lot was worth: turnover ÷ lots ÷ close is the
-- number of quote bases in one lot. If the seed's `quote_units_per_lot` is off
-- by 10x — GOLD per 10 g read as per gram — every notional, OI value and
-- lot-sized page is off by 10x too, and no price test would notice.
--
-- Median over each verified code's last 60 liquid sessions, so one volatile
-- day (turnover is at the average traded price, the close is the settlement)
-- cannot fail it, and a wrong seed row always does. Unverified codes are
-- reported by the warn-level twin below, not failed.
with liquid as (
    select contract_code, implied_quote_units_per_lot, quote_units_per_lot,
           row_number() over (partition by contract_code order by trade_date desc) as recency
    from {{ ref('int_mcx__futures_sessions') }}
    where is_spec_verified and volume_lots >= 10 and implied_quote_units_per_lot is not null
)

select
    contract_code,
    max(quote_units_per_lot)                                  as seeded,
    median(implied_quote_units_per_lot)                       as implied
from liquid
where recency <= 60
group by contract_code
having median(implied_quote_units_per_lot) / max(quote_units_per_lot) not between 0.9 and 1.1
