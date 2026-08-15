with

depletion_rates as (

    select * from {{ ref('int_stock_depletion_rate') }}

),

current_levels as (

    select * from {{ ref('int_inventory_current_level') }}

),

demand_supply as (

    select
        depletion_rates.product_id,
        depletion_rates.location_id,
        depletion_rates.current_quantity,
        depletion_rates.daily_depletion_rate as daily_demand_rate,
        depletion_rates.outbound_last_30d as demand_last_30d,
        current_levels.total_inbound as total_supply,
        current_levels.total_outbound as total_demand,
        depletion_rates.estimated_days_of_stock,
        case
            when current_levels.total_outbound > 0
                then current_levels.total_inbound * 1.0
                    / current_levels.total_outbound
            else null
        end as supply_to_demand_ratio,
        case
            when depletion_rates.daily_depletion_rate > 0
                and depletion_rates.estimated_days_of_stock < 7
                then 'supply_shortage'
            when depletion_rates.daily_depletion_rate > 0
                and depletion_rates.estimated_days_of_stock between 7 and 30
                then 'balanced'
            when depletion_rates.daily_depletion_rate > 0
                and depletion_rates.estimated_days_of_stock > 30
                then 'oversupplied'
            when depletion_rates.daily_depletion_rate = 0
                and depletion_rates.current_quantity > 0
                then 'no_demand'
            else 'no_stock'
        end as supply_demand_status,
        current_levels.last_movement_at

    from depletion_rates

    left join current_levels
        on depletion_rates.product_id = current_levels.product_id
        and depletion_rates.location_id = current_levels.location_id

)

select * from demand_supply
