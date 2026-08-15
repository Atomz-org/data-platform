with

current_level as (

    select
        product_id,
        location_id,
        current_quantity
    from {{ ref('int_inventory_current_level') }}

),

depletion_rate as (

    select
        product_id,
        location_id,
        daily_depletion_rate
    from {{ ref('int_stock_depletion_rate') }}

),

final as (

    select
        cl.product_id,
        cl.location_id,
        cl.current_quantity,
        coalesce(dr.daily_depletion_rate, 0) as daily_depletion_rate,
        coalesce(dr.daily_depletion_rate, 0) * 7 as weekly_depletion_rate,
        case
            when coalesce(dr.daily_depletion_rate, 0) > 0
                then round(cast(cl.current_quantity / (dr.daily_depletion_rate * 7) as {{ dbt.type_float() }}), 1)
            else null
        end as weeks_of_supply,
        case
            when coalesce(dr.daily_depletion_rate, 0) = 0 then 'no_demand'
            when cl.current_quantity / (dr.daily_depletion_rate * 7) > 8 then 'overstocked'
            when cl.current_quantity / (dr.daily_depletion_rate * 7) > 4 then 'healthy'
            when cl.current_quantity / (dr.daily_depletion_rate * 7) > 2 then 'low'
            else 'critical'
        end as supply_status
    from current_level as cl
    left join depletion_rate as dr
        on cl.product_id = dr.product_id
        and cl.location_id = dr.location_id

)

select * from final
