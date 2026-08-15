with

recipe_ingredients as (

    select * from {{ ref('stg_recipe_ingredients') }}

),

ingredient_prices as (

    select * from {{ ref('stg_ingredient_prices') }}

),

ingredients as (

    select * from {{ ref('stg_ingredients') }}

),

current_prices as (

    select
        ingredient_id,
        unit_cost,
        row_number() over (
            partition by ingredient_id
            order by effective_from_date desc
        ) as price_recency_rank

    from ingredient_prices
    where effective_to_date is null
        or effective_to_date >= current_date

),

latest_prices as (

    select
        ingredient_id,
        unit_cost

    from current_prices
    where price_recency_rank = 1

),

cost_breakdown as (

    select
        ri.recipe_ingredient_id,
        ri.recipe_id,
        ri.ingredient_id,
        i.ingredient_name,
        i.ingredient_category,
        ri.quantity,
        ri.quantity_unit,
        lp.unit_cost as ingredient_unit_cost,
        ri.quantity * coalesce(lp.unit_cost, 0) as ingredient_line_cost

    from recipe_ingredients as ri
    left join ingredients as i
        on ri.ingredient_id = i.ingredient_id
    left join latest_prices as lp
        on ri.ingredient_id = lp.ingredient_id

)

select * from cost_breakdown
