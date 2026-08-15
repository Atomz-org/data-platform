with monthly_refunds as (
    select {{ sf_date_trunc('month', "requested_date") }} as refund_month, count(*) as refunds, sum(refund_amount) as total_refunds
    from {{ ref('fct_refunds') }}
    group by 1
),
monthly_orders as (
    select {{ sf_date_trunc('month', "ordered_at") }} as order_month, count(*) as total_orders, sum(order_total) as total_revenue
    from {{ ref('stg_orders') }}
    group by 1
),
final as (
    select
        mo.order_month,
        mo.total_orders,
        coalesce(mr.refunds, 0) as refunds,
        round(coalesce(mr.refunds, 0) * 100.0 / nullif(mo.total_orders, 0), 2) as refund_rate_pct,
        round(coalesce(mr.total_refunds, 0) * 100.0 / nullif(mo.total_revenue, 0), 2) as refund_value_rate_pct
    from monthly_orders as mo
    left join monthly_refunds as mr on mo.order_month = mr.refund_month
)
select * from final
