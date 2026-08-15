with

daily_sales as (
    select product_id, sale_date, units_sold
    from {{ ref('fct_product_sales') }}
),

per_product as (
    select
        product_id,
        round(avg(units_sold), 2) as mean_daily_qty,
        round(percentile_cont(0.50) within group (order by units_sold), 2) as median_daily_qty,
        round(percentile_cont(0.75) within group (order by units_sold), 2) as p75_daily_qty,
        round(percentile_cont(0.90) within group (order by units_sold), 2) as p90_daily_qty,
        min(units_sold) as min_daily_qty,
        max(units_sold) as max_daily_qty,
        count(*) as active_days
    from daily_sales
    group by 1
)

select * from per_product
