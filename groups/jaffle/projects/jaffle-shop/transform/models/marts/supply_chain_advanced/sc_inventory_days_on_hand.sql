with

inventory as (

    select
        product_id,
        location_id,
        current_quantity
    from {{ ref('int_inventory_current_level') }}

),

depletion as (

    select
        product_id,
        location_id,
        daily_depletion_rate
    from {{ ref('int_stock_depletion_rate') }}

),

final as (

    select
        inv.product_id,
        inv.location_id,
        inv.current_quantity,
        coalesce(dep.daily_depletion_rate, 0) as daily_usage_rate,
        case
            when coalesce(dep.daily_depletion_rate, 0) > 0
            then inv.current_quantity / dep.daily_depletion_rate
            else null
        end as days_on_hand,
        case
            when coalesce(dep.daily_depletion_rate, 0) > 0
                and inv.current_quantity / dep.daily_depletion_rate > 60
            then 'excess'
            when coalesce(dep.daily_depletion_rate, 0) > 0
                and inv.current_quantity / dep.daily_depletion_rate > 30
            then 'adequate'
            when coalesce(dep.daily_depletion_rate, 0) > 0
                and inv.current_quantity / dep.daily_depletion_rate > 7
            then 'low'
            when coalesce(dep.daily_depletion_rate, 0) > 0
            then 'critical'
            else 'no_usage_data'
        end as inventory_health
    from inventory as inv
    left join depletion as dep
        on inv.product_id = dep.product_id
        and inv.location_id = dep.location_id

)

select * from final
