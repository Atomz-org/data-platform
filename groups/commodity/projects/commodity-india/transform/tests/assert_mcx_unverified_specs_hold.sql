{{ config(severity='warn') }}
-- The unverified twin of `assert_mcx_quote_basis_matches_turnover`: codes whose
-- specification was published, not derived, because they did not trade when
-- the seed was written. A row here is the evidence to correct the seed and
-- flip `is_spec_verified`.
with liquid as (
    select contract_code, implied_quote_units_per_lot, quote_units_per_lot
    from {{ ref('int_mcx__futures_sessions') }}
    where not is_spec_verified and volume_lots >= 10 and implied_quote_units_per_lot is not null
)

select contract_code, max(quote_units_per_lot) as seeded, median(implied_quote_units_per_lot) as implied
from liquid
group by contract_code
having median(implied_quote_units_per_lot) / max(quote_units_per_lot) not between 0.9 and 1.1
