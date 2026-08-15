with

daily_refunds as (
    select
        requested_date,
        count(*) as refund_count,
        sum(refund_amount) as total_refund_amount
    from {{ ref('fct_refunds') }}
    group by 1
),

daily_orders as (
    select
        ordered_at as order_date,
        count(*) as total_orders,
        sum(order_total) as total_revenue
    from {{ ref('stg_orders') }}
    group by 1
),

combined as (
    select
        daily_ord.order_date as metric_date,
        coalesce(dr.refund_count, 0) as refund_count,
        daily_ord.total_orders,
        round(coalesce(dr.refund_count, 0) * 100.0 / nullif(daily_ord.total_orders, 0), 2) as refund_rate_pct,
        round(coalesce(dr.total_refund_amount, 0) * 100.0 / nullif(daily_ord.total_revenue, 0), 2) as refund_value_rate_pct
    from daily_orders as daily_ord
    left join daily_refunds as dr on daily_ord.order_date = dr.requested_date
),

trended as (
    select
        metric_date,
        refund_rate_pct,
        refund_value_rate_pct,
        refund_count,
        avg(refund_rate_pct) over (order by metric_date rows between 6 preceding and current row) as refund_rate_7d_ma,
        avg(refund_rate_pct) over (order by metric_date rows between 27 preceding and current row) as refund_rate_28d_ma,
        case
            when refund_rate_pct > avg(refund_rate_pct) over (
                order by metric_date rows between 27 preceding and current row
            ) * 2 then 'spike'
            else 'normal'
        end as refund_anomaly
    from combined
)

select * from trended
