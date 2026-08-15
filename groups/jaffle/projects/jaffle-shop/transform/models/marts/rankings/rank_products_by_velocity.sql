with

product_velocity as (
    select
        product_id,
        count(distinct sale_date) as active_days,
        sum(units_sold) as total_units,
        round(sum(units_sold) * 1.0 / nullif(count(distinct sale_date), 0), 2) as units_per_day
    from {{ ref('fct_product_sales') }}
    group by 1
),

ranked as (
    select
        product_id,
        active_days,
        total_units,
        units_per_day,
        rank() over (order by units_per_day desc) as velocity_rank,
        ntile(4) over (order by units_per_day desc) as velocity_quartile
    from product_velocity
)

select * from ranked
