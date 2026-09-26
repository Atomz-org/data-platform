-- On a day a contract traded, its open lies inside its own high-low range. A
-- row here is a parsing fault (columns crossed) rather than a market event.
select session_id, open_price, high_price, low_price
from {{ ref('int_mcx__futures_sessions') }}
where is_traded
  and (open_price > high_price * 1.0001 or open_price < low_price * 0.9999 or low_price > high_price)
