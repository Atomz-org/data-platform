with

recipe_cost_breakdown as (

    select * from {{ ref('int_recipe_cost_breakdown') }}

),

recipe_totals as (

    select
        recipe_id,
        count(distinct ingredient_id) as ingredient_count,
        sum(ingredient_line_cost) as total_ingredient_cost,
        max(ingredient_line_cost) as highest_ingredient_cost,
        min(ingredient_line_cost) as lowest_ingredient_cost

    from recipe_cost_breakdown
    group by recipe_id

)

select * from recipe_totals
