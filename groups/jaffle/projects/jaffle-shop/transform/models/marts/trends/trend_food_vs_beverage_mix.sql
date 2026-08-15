with

ps as (
    select * from {{ ref('fct_product_sales') }}
),

p as (
    select * from {{ ref('stg_products') }}
),

daily_product_mix as (
    select
        ps.sale_date,
        p.product_type,
        sum(ps.units_sold) as units_sold,
        sum(ps.daily_revenue) as revenue
    from ps
    inner join p on ps.product_id = p.product_id
    group by 1, 2
),

pivoted as (
    select
        sale_date,
        sum(case when product_type = 'food' then revenue else 0 end) as food_revenue,
        sum(case when product_type = 'beverage' then revenue else 0 end) as beverage_revenue,
        sum(revenue) as total_revenue,
        round(sum(case when product_type = 'food' then revenue else 0 end) * 100.0
            / nullif(sum(revenue), 0), 2) as food_pct
    from daily_product_mix
    group by 1
),

trended as (
    select
        sale_date,
        food_revenue,
        beverage_revenue,
        total_revenue,
        food_pct,
        100.0 - food_pct as beverage_pct,
        avg(food_pct) over (order by sale_date rows between 6 preceding and current row) as food_pct_7d_ma,
        avg(food_pct) over (order by sale_date rows between 27 preceding and current row) as food_pct_28d_ma,
        lag(food_pct, 7) over (order by sale_date) as food_pct_last_week
    from pivoted
)

select * from trended
