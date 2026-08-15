with

ps as (
    select * from {{ ref('fct_product_sales') }}
),

rc as (
    select * from {{ ref('fct_recipe_costs') }}
),

monthly_margin as (
    select
        {{ sf_date_trunc('month', "ps.sale_date") }} as sale_month,
        sum(ps.daily_revenue) as revenue,
        sum(ps.units_sold * coalesce(rc.ingredient_line_cost, 0)) as cogs,
        round((sum(ps.daily_revenue) - sum(ps.units_sold * coalesce(rc.ingredient_line_cost, 0))) * 100.0
            / nullif(sum(ps.daily_revenue), 0), 2) as gross_margin_pct
    from ps
    left join rc on ps.product_id = rc.menu_item_id
    group by 1
),

compared as (
    select
        sale_month,
        gross_margin_pct as current_margin,
        lag(gross_margin_pct, 12) over (order by sale_month) as prior_year_margin,
        gross_margin_pct - lag(gross_margin_pct, 12) over (order by sale_month) as margin_yoy_change_pp
    from monthly_margin
)

select * from compared
