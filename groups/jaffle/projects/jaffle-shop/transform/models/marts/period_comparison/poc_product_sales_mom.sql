with

monthly_products as (
    select
        month_start,
        product_id,
        monthly_units,
        monthly_revenue
    from {{ ref('met_monthly_product_sales') }}
),

compared as (
    select
        month_start,
        product_id,
        monthly_units as current_qty,
        monthly_revenue as current_revenue,
        lag(monthly_units) over (partition by product_id order by month_start) as prior_month_qty,
        lag(monthly_revenue) over (partition by product_id order by month_start) as prior_month_revenue,
        round(((monthly_units - lag(monthly_units) over (partition by product_id order by month_start))) * 100.0
            / nullif(lag(monthly_units) over (partition by product_id order by month_start), 0), 2) as qty_mom_change_pct,
        round(((monthly_revenue - lag(monthly_revenue) over (partition by product_id order by month_start))) * 100.0
            / nullif(lag(monthly_revenue) over (partition by product_id order by month_start), 0), 2) as revenue_mom_change_pct
    from monthly_products
)

select * from compared
