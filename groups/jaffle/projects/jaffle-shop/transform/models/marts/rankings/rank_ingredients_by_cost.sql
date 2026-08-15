with

ingredient_cost as (
    select
        ingredient_id,
        sum(ingredient_line_cost) as total_cost,
        sum(quantity) as total_quantity,
        round(sum(ingredient_line_cost) * 1.0 / nullif(sum(quantity), 0), 2) as avg_unit_cost
    from {{ ref('int_recipe_cost_breakdown') }}
    group by 1
),

ranked as (
    select
        ingredient_id,
        total_cost,
        total_quantity,
        avg_unit_cost,
        rank() over (order by total_cost desc) as cost_rank,
        round(total_cost * 100.0 / nullif(sum(total_cost) over (), 0), 2) as cost_share_pct,
        sum(total_cost) over (order by total_cost desc) as cumulative_cost
    from ingredient_cost
)

select * from ranked
