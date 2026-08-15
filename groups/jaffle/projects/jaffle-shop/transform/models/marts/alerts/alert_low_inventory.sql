with

inventory_levels as (
    select
        product_id,
        location_id,
        current_quantity
    from {{ ref('int_inventory_current_level') }}
),

alerts as (
    select
        product_id,
        location_id,
        current_quantity,
        'low_inventory' as alert_type,
        case
            when current_quantity <= 0 then 'critical'
            when current_quantity < 10 then 'warning'
            else 'info'
        end as severity
    from inventory_levels
    where current_quantity < 10
)

select * from alerts
