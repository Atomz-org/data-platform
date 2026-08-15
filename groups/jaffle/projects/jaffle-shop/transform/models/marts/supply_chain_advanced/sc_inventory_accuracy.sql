select
    sc.product_id,
    sc.location_id,
    cast(sc.current_quantity as integer) as system_quantity,
    lp.quantity_available as physical_quantity,
    lp.counted_at as last_counted_at,
    cast(sc.current_quantity as integer) - coalesce(lp.quantity_available, 0) as variance_units,
    case
        when coalesce(lp.quantity_available, 0) > 0
        then abs(cast(sc.current_quantity as integer) - lp.quantity_available)
            / cast(lp.quantity_available as {{ dbt.type_float() }}) * 100
        else null
    end as variance_pct,
    case
        when abs(cast(sc.current_quantity as integer) - coalesce(lp.quantity_available, 0))
            / nullif(cast(lp.quantity_available as {{ dbt.type_float() }}), 0) > 0.10
        then 'significant_variance'
        when abs(cast(sc.current_quantity as integer) - coalesce(lp.quantity_available, 0))
            / nullif(cast(lp.quantity_available as {{ dbt.type_float() }}), 0) > 0.03
        then 'minor_variance'
        else 'accurate'
    end as accuracy_status

from {{ ref('int_inventory_current_level') }} as sc

left join (
    select
        product_id,
        location_id,
        max_by(quantity_available, counted_at) as quantity_available,
        max(counted_at) as counted_at
    from {{ ref('stg_inventory_counts') }}
    group by product_id, location_id
) as lp
    on sc.product_id = lp.product_id
    and sc.location_id = lp.location_id
