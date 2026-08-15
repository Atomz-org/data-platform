with

stock_alerts as (

    select * from {{ ref('rpt_stock_alerts') }}

)

select
    location_id,
    product_id,
    current_quantity,
    reorder_point,
    estimated_days_of_stock,
    stock_alert_level,
    case
        when stock_alert_level = 'stockout' then 'critical'
        when stock_alert_level = 'low_stock' then 'warning'
        else 'ok'
    end as urgency,
    case
        when estimated_days_of_stock <= 0 then 'out_of_stock'
        when estimated_days_of_stock <= 3 then 'reorder_immediately'
        when estimated_days_of_stock <= 7 then 'reorder_soon'
        else 'adequate'
    end as action_needed

from stock_alerts
