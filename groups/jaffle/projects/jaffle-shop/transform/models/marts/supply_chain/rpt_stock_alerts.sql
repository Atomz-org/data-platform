with

current_levels as (

    select * from {{ ref('int_inventory_current_level') }}

),

reorder_points as (

    select * from {{ ref('int_reorder_point_calc') }}

),

alerts as (

    select
        reorder_points.product_id,
        reorder_points.location_id,
        reorder_points.current_quantity,
        reorder_points.daily_depletion_rate,
        reorder_points.estimated_days_of_stock,
        reorder_points.supplier_avg_lead_time_days,
        reorder_points.reorder_point,
        reorder_points.suggested_reorder_quantity,
        reorder_points.needs_reorder,
        case
            when reorder_points.current_quantity <= 0
                then 'out_of_stock'
            when reorder_points.estimated_days_of_stock is not null
                and reorder_points.estimated_days_of_stock
                    <= reorder_points.supplier_avg_lead_time_days
                then 'critical'
            when reorder_points.needs_reorder = true
                then 'reorder_needed'
            when reorder_points.estimated_days_of_stock is not null
                and reorder_points.estimated_days_of_stock <= 14
                then 'low_stock'
            else 'healthy'
        end as stock_alert_level,
        current_levels.last_movement_at

    from reorder_points

    left join current_levels
        on reorder_points.product_id = current_levels.product_id
        and reorder_points.location_id = current_levels.location_id

)

select * from alerts
