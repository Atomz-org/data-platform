with

depletion as (
    select
        product_id,
        location_id,
        current_quantity,
        daily_depletion_rate,
        case
            when daily_depletion_rate > 0
            then round(current_quantity * 1.0 / daily_depletion_rate, 1)
            else null
        end as estimated_days_of_stock
    from {{ ref('int_stock_depletion_rate') }}
),

alerts as (
    select
        product_id,
        location_id,
        current_quantity,
        daily_depletion_rate,
        estimated_days_of_stock,
        'stockout_risk' as alert_type,
        case
            when estimated_days_of_stock <= 1 then 'critical'
            when estimated_days_of_stock <= 3 then 'warning'
            else 'info'
        end as severity
    from depletion
    where estimated_days_of_stock <= 7
)

select * from alerts
