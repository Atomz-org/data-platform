with

o as (
    select * from {{ ref('stg_orders') }}
),

r as (
    select * from {{ ref('fct_refunds') }}
),

daily_refund_rate as (
    select
        o.ordered_at as order_date,
        o.location_id,
        count(distinct o.order_id) as total_orders,
        count(distinct r.refund_id) as refund_count,
        round(count(distinct r.refund_id) * 100.0 / nullif(count(distinct o.order_id), 0), 2) as refund_rate_pct
    from o
    left join r on o.order_id = r.order_id
    group by 1, 2
),

alerts as (
    select
        order_date,
        location_id,
        total_orders,
        refund_count,
        refund_rate_pct,
        'high_refund_rate' as alert_type,
        case
            when refund_rate_pct > 10 then 'critical'
            else 'warning'
        end as severity
    from daily_refund_rate
    where refund_rate_pct > 5
)

select * from alerts
