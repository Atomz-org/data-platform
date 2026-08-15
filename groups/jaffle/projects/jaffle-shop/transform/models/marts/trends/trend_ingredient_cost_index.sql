with

monthly_cost as (
    select
        price_month,
        avg(avg_unit_cost) as avg_ingredient_cost,
        count(distinct ingredient_id) as ingredients_tracked
    from {{ ref('int_ingredient_cost_trend') }}
    group by 1
),

base_cost as (
    select avg(avg_ingredient_cost) as baseline_cost
    from monthly_cost
),

trended as (
    select
        mc.price_month,
        mc.avg_ingredient_cost,
        mc.ingredients_tracked,
        round(mc.avg_ingredient_cost * 100.0 / nullif(bc.baseline_cost, 0), 2) as cost_index,
        lag(mc.avg_ingredient_cost) over (order by mc.price_month) as prev_month_cost,
        case
            when lag(mc.avg_ingredient_cost) over (order by mc.price_month) > 0
            then (mc.avg_ingredient_cost - lag(mc.avg_ingredient_cost) over (order by mc.price_month))
                / lag(mc.avg_ingredient_cost) over (order by mc.price_month) * 100
            else null
        end as mom_change_pct,
        case
            when mc.avg_ingredient_cost > lag(mc.avg_ingredient_cost, 3) over (order by mc.price_month)
            then 'increasing'
            when mc.avg_ingredient_cost < lag(mc.avg_ingredient_cost, 3) over (order by mc.price_month)
            then 'decreasing'
            else 'stable'
        end as cost_trend
    from monthly_cost as mc
    cross join base_cost as bc
)

select * from trended
