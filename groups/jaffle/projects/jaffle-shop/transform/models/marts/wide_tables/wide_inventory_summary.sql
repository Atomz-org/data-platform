with

current_level as (

    select * from {{ ref('int_inventory_current_level') }}

),

inventory_value as (

    select * from {{ ref('int_inventory_value_by_location') }}

),

turnover as (

    select * from {{ ref('rpt_inventory_turnover') }}

),

stock_alerts as (

    select * from {{ ref('rpt_stock_alerts') }}

)

select
    cl.product_id,
    cl.location_id,
    cl.current_quantity,
    iv.inventory_value,
    0 as safety_stock,
    t.inventory_turnover_ratio,
    sa.stock_alert_level as stock_alert,
    sa.reorder_point,
    sa.estimated_days_of_stock,
    case
        when sa.stock_alert_level = 'stockout' then 'critical'
        when sa.stock_alert_level = 'low_stock' then 'warning'
        when 0 < 2 then 'slow_moving'
        else 'healthy'
    end as inventory_health

from current_level cl
left join inventory_value iv
    on cl.product_id = iv.product_id and cl.location_id = iv.location_id
left join turnover t
    on cl.product_id = t.product_id and cl.location_id = t.location_id
left join stock_alerts sa
    on cl.product_id = sa.product_id and cl.location_id = sa.location_id
