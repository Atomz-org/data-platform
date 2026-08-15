with

ingredient_usage as (
    select
        ingredient_id,
        sum(total_quantity_used) as total_usage,
        count(distinct order_date) as active_days
    from {{ ref('fct_ingredient_usage') }}
    group by 1
),

ranked as (
    select
        ingredient_id,
        total_usage,
        active_days,
        round(total_usage * 1.0 / nullif(active_days, 0), 2) as usage_per_day,
        rank() over (order by total_usage desc) as usage_rank,
        ntile(5) over (order by total_usage desc) as usage_quintile
    from ingredient_usage
)

select * from ranked
