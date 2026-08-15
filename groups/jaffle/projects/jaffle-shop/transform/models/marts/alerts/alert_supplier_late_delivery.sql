with

late_deliveries as (
    select
        actual_arrival_at,
        supplier_id,
        purchase_order_id,
        actual_transit_days,
        expected_transit_days,
        case when not is_on_time then actual_transit_days - expected_transit_days else 0 end as days_late
    from {{ ref('fct_deliveries') }}
    where not is_on_time
),

alerts as (
    select
        actual_arrival_at,
        supplier_id,
        purchase_order_id,
        actual_transit_days,
        days_late,
        'supplier_late_delivery' as alert_type,
        case
            when days_late > 7 then 'critical'
            when days_late > 3 then 'warning'
            else 'info'
        end as severity
    from late_deliveries
    where days_late > 0
)

select * from alerts
