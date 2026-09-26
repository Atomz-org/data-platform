-- Two seeds describe the same MCX lots: `mcx_contract_lots` (landed-equivalent
-- sizing) and `mcx_products` (the exchange's own series). A code in both must
-- hold the same number of quote bases per lot, in the group's unit factors.
with lots as (
    select
        l.contract_code,
        l.lot_size * lu.base_units_per_unit / (l.quote_size * qu.base_units_per_unit) as quote_units_per_lot
    from {{ ref('mcx_contract_lots') }} as l
    inner join {{ ref('units_of_measure') }} as lu on lu.unit_code = l.lot_unit
    inner join {{ ref('units_of_measure') }} as qu on qu.unit_code = l.quote_unit
)

select l.contract_code, l.quote_units_per_lot as from_contract_lots, p.quote_units_per_lot as from_mcx_products
from lots as l
inner join {{ ref('mcx_products') }} as p on p.contract_code = l.contract_code
where abs(l.quote_units_per_lot - p.quote_units_per_lot) > 0.0001 * p.quote_units_per_lot
