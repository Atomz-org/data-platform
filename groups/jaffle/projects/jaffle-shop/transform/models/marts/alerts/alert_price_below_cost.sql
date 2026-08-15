with

ps as (
    select * from {{ ref('fct_product_sales') }}
),

rc as (
    select * from {{ ref('fct_recipe_costs') }}
),

product_economics as (
    select
        ps.product_id,
        ps.sale_date,
        round(ps.daily_revenue * 1.0 / nullif(ps.units_sold, 0), 2) as selling_price,
        rc.ingredient_line_cost as unit_cost
    from ps
    inner join rc on ps.product_id = rc.menu_item_id
),

alerts as (
    select
        product_id,
        sale_date,
        selling_price,
        unit_cost,
        selling_price - unit_cost as margin,
        'price_below_cost' as alert_type,
        'critical' as severity
    from product_economics
    where selling_price < unit_cost
      and unit_cost > 0
)

select * from alerts
