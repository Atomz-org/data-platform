with

stock_alerts as (

    select * from {{ ref('rpt_stock_alerts') }}

)

select
    location_id,
    product_id,
    current_quantity,
    reorder_point,
    suggested_reorder_quantity,
    estimated_days_of_stock,
    stock_alert_level,
    current_timestamp as exported_at,
    'auto_reorder' as reorder_trigger

from stock_alerts
where stock_alert_level in ('stockout', 'low_stock')
