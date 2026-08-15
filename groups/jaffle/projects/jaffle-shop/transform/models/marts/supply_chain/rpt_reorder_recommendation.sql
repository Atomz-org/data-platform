with

stock_alerts as (

    select * from {{ ref('rpt_stock_alerts') }}

),

reorder_points as (

    select * from {{ ref('int_reorder_point_calc') }}

),

products as (

    select * from {{ ref('stg_products') }}

),

locations as (

    select * from {{ ref('stg_locations') }}

),

recommendations as (

    select
        stock_alerts.product_id,
        products.product_name,
        products.product_type,
        stock_alerts.location_id,
        locations.location_name,
        stock_alerts.current_quantity,
        stock_alerts.stock_alert_level,
        reorder_points.reorder_point,
        reorder_points.suggested_reorder_quantity,
        reorder_points.daily_depletion_rate,
        reorder_points.estimated_days_of_stock,
        reorder_points.supplier_avg_lead_time_days,
        case
            when stock_alerts.stock_alert_level = 'out_of_stock'
                then reorder_points.suggested_reorder_quantity * 1.5
            when stock_alerts.stock_alert_level = 'critical'
                then reorder_points.suggested_reorder_quantity * 1.25
            else reorder_points.suggested_reorder_quantity
        end as recommended_order_quantity,
        case
            when stock_alerts.stock_alert_level = 'out_of_stock' then 1
            when stock_alerts.stock_alert_level = 'critical' then 2
            when stock_alerts.stock_alert_level = 'reorder_needed' then 3
            when stock_alerts.stock_alert_level = 'low_stock' then 4
            else 5
        end as priority_rank

    from stock_alerts

    inner join reorder_points
        on stock_alerts.product_id = reorder_points.product_id
        and stock_alerts.location_id = reorder_points.location_id

    left join products
        on stock_alerts.product_id = products.product_id

    left join locations
        on stock_alerts.location_id = locations.location_id

    where stock_alerts.stock_alert_level != 'healthy'

)

select * from recommendations
