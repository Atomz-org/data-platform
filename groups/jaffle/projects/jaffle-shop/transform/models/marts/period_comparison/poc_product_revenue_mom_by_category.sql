with

ps as (
    select * from {{ ref('fct_product_sales') }}
),

p as (
    select * from {{ ref('stg_products') }}
),

monthly_category as (
    select
        {{ sf_date_trunc('month', "ps.sale_date") }} as sale_month,
        p.product_type as category,
        sum(ps.daily_revenue) as category_revenue,
        sum(ps.units_sold) as category_units
    from ps
    inner join p on ps.product_id = p.product_id
    group by 1, 2
),

compared as (
    select
        sale_month,
        category,
        category_revenue as current_revenue,
        lag(category_revenue) over (partition by category order by sale_month) as prior_month_revenue,
        category_units as current_units,
        lag(category_units) over (partition by category order by sale_month) as prior_month_units,
        round(((category_revenue - lag(category_revenue) over (partition by category order by sale_month))) * 100.0
            / nullif(lag(category_revenue) over (partition by category order by sale_month), 0), 2) as revenue_mom_pct,
        round(((category_units - lag(category_units) over (partition by category order by sale_month))) * 100.0
            / nullif(lag(category_units) over (partition by category order by sale_month), 0), 2) as units_mom_pct
    from monthly_category
)

select * from compared
