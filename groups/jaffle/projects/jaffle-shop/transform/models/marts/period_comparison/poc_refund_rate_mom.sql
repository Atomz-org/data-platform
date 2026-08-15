with

monthly_refunds as (
    select
        {{ sf_date_trunc('month', "requested_date") }} as refund_month,
        count(*) as refund_count,
        sum(refund_amount) as total_refunds
    from {{ ref('fct_refunds') }}
    group by 1
),

monthly_orders as (
    select
        {{ sf_date_trunc('month', "ordered_at") }} as order_month,
        count(*) as total_orders,
        sum(order_total) as total_revenue
    from {{ ref('stg_orders') }}
    group by 1
),

combined as (
    select
        mo.order_month as metric_month,
        coalesce(mr.refund_count, 0) as refund_count,
        mo.total_orders,
        round(coalesce(mr.refund_count, 0) * 100.0 / nullif(mo.total_orders, 0), 2) as refund_rate_pct
    from monthly_orders as mo
    left join monthly_refunds as mr on mo.order_month = mr.refund_month
),

compared as (
    select
        metric_month,
        refund_rate_pct as current_rate,
        lag(refund_rate_pct) over (order by metric_month) as prior_month_rate,
        refund_rate_pct - lag(refund_rate_pct) over (order by metric_month) as rate_change_pp,
        refund_count as current_refunds,
        lag(refund_count) over (order by metric_month) as prior_month_refunds
    from combined
)

select * from compared
