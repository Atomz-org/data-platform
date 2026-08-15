with

ingredients as (
    select ingredient_id, ingredient_unit_cost, ingredient_line_cost
    from {{ ref('int_recipe_cost_breakdown') }}
),

per_ingredient as (
    select
        ingredient_id,
        round(avg(ingredient_unit_cost), 2) as mean_ingredient_unit_cost,
        round(percentile_cont(0.50) within group (order by ingredient_unit_cost), 2) as median_cost,
        round(percentile_cont(0.90) within group (order by ingredient_unit_cost), 2) as p90_cost,
        min(ingredient_unit_cost) as min_cost,
        max(ingredient_unit_cost) as max_cost,
        count(*) as usage_records
    from ingredients
    group by 1
)

select * from per_ingredient
