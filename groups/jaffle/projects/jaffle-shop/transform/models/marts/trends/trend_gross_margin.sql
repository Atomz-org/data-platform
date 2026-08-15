with

ps as (
    select * from {{ ref('fct_product_sales') }}
),

rc as (
    select * from {{ ref('fct_recipe_costs') }}
),

daily_financials as (
    select
        ps.sale_date,
        sum(ps.daily_revenue) as revenue,
        sum(ps.units_sold * coalesce(rc.ingredient_line_cost, 0)) as cogs
    from ps
    left join rc on ps.product_id = rc.menu_item_id
    group by 1
),

trended as (
    select
        sale_date,
        revenue,
        cogs,
        revenue - cogs as gross_profit,
        round((revenue - cogs) * 100.0 / nullif(revenue, 0), 2) as gross_margin_pct,
        avg(round((revenue - cogs) * 100.0 / nullif(revenue, 0), 2)) over (
            order by sale_date rows between 6 preceding and current row
        ) as margin_7d_ma,
        avg(round((revenue - cogs) * 100.0 / nullif(revenue, 0), 2)) over (
            order by sale_date rows between 27 preceding and current row
        ) as margin_28d_ma,
        case
            when round((revenue - cogs) * 100.0 / nullif(revenue, 0), 2) < avg(
                round((revenue - cogs) * 100.0 / nullif(revenue, 0), 2)
            ) over (order by sale_date rows between 27 preceding and current row) - 5
            then 'margin_pressure'
            else 'healthy'
        end as margin_status
    from daily_financials
)

select * from trended
