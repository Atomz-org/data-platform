with

ps as (
    select * from {{ ref('fct_product_sales') }}
),

rc as (
    select * from {{ ref('fct_recipe_costs') }}
),

product_margin as (
    select
        ps.product_id,
        sum(ps.daily_revenue) as total_revenue,
        sum(ps.units_sold * coalesce(rc.ingredient_line_cost, 0)) as total_cogs,
        round((sum(ps.daily_revenue) - sum(ps.units_sold * coalesce(rc.ingredient_line_cost, 0))) * 100.0
            / nullif(sum(ps.daily_revenue), 0), 2) as gross_margin_pct
    from ps
    left join rc on ps.product_id = rc.menu_item_id
    group by 1
),

ranked as (
    select
        product_id,
        total_revenue,
        total_cogs,
        gross_margin_pct,
        rank() over (order by gross_margin_pct desc) as margin_rank,
        ntile(4) over (order by gross_margin_pct desc) as margin_quartile,
        case
            when gross_margin_pct >= 70 then 'high_margin'
            when gross_margin_pct >= 50 then 'medium_margin'
            else 'low_margin'
        end as margin_band
    from product_margin
)

select * from ranked
