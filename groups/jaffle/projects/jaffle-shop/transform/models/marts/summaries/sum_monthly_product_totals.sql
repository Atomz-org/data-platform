with final as (
    select
        month_start,
        product_id,
        monthly_units,
        monthly_revenue,
        round(monthly_revenue * 1.0 / nullif(monthly_units, 0), 2) as avg_unit_price,
        lag(monthly_revenue) over (partition by product_id order by month_start) as prior_month_revenue,
        round(((monthly_revenue - lag(monthly_revenue) over (partition by product_id order by month_start))) * 100.0
            / nullif(lag(monthly_revenue) over (partition by product_id order by month_start), 0), 2) as mom_change_pct,
        rank() over (partition by month_start order by monthly_revenue desc) as revenue_rank
    from {{ ref('met_monthly_product_sales') }}
)
select * from final
