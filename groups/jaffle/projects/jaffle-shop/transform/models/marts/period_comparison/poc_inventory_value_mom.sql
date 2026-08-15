with

monthly_inventory as (
    select
        month_start,
        location_id,
        total_units_on_hand,
        monthly_movements
    from {{ ref('met_monthly_inventory_metrics') }}
),

compared as (
    select
        month_start,
        location_id,
        total_units_on_hand as current_value,
        lag(total_units_on_hand) over (partition by location_id order by month_start) as prior_month_value,
        round(((total_units_on_hand - lag(total_units_on_hand) over (partition by location_id order by month_start))) * 100.0
            / nullif(lag(total_units_on_hand) over (partition by location_id order by month_start), 0), 2) as value_mom_pct,
        monthly_movements as current_movement,
        lag(monthly_movements) over (partition by location_id order by month_start) as prior_month_movement
    from monthly_inventory
)

select * from compared
