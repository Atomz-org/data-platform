with final as (
    select
        month_start,
        location_id,
        monthly_revenue,
        monthly_orders,
        round(monthly_revenue * 1.0 / nullif(monthly_orders, 0), 2) as avg_order_value,
        lag(round(monthly_revenue * 1.0 / nullif(monthly_orders, 0), 2)) over (
            partition by location_id order by month_start
        ) as prior_month_aov
    from {{ ref('met_monthly_revenue_by_store') }}
)
select * from final
