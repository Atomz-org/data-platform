with

current_levels as (

    select * from {{ ref('int_inventory_current_level') }}

),

inventory_movements as (

    select * from {{ ref('stg_inventory_movements') }}

),

recent_outbound as (

    select
        product_id,
        location_id,
        sum(abs(quantity)) as total_outbound_last_30d,
        count(movement_id) as count_outbound_events,
        min(moved_at) as earliest_outbound,
        max(moved_at) as latest_outbound,
        {{ dbt.datediff('min(moved_at)', 'max(moved_at)', 'day') }} as days_span

    from inventory_movements

    where movement_type = 'outbound'
        and moved_at >= {{ dbt.dateadd('day', -30, dbt.current_timestamp()) }}

    group by product_id, location_id

),

depletion_rates as (

    select
        current_levels.product_id,
        current_levels.location_id,
        current_levels.current_quantity,
        coalesce(recent_outbound.total_outbound_last_30d, 0) as outbound_last_30d,
        coalesce(recent_outbound.count_outbound_events, 0) as outbound_events_last_30d,
        case
            when coalesce(recent_outbound.total_outbound_last_30d, 0) > 0
                then recent_outbound.total_outbound_last_30d / 30.0
            else 0
        end as daily_depletion_rate,
        case
            when coalesce(recent_outbound.total_outbound_last_30d, 0) > 0
                then current_levels.current_quantity
                    / (recent_outbound.total_outbound_last_30d / 30.0)
            else null
        end as estimated_days_of_stock

    from current_levels

    left join recent_outbound
        on current_levels.product_id = recent_outbound.product_id
        and current_levels.location_id = recent_outbound.location_id

)

select * from depletion_rates
