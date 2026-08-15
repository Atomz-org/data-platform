with

recipe_cost_breakdown as (

    select * from {{ ref('int_recipe_cost_breakdown') }}

),

recipes as (

    select * from {{ ref('stg_recipes') }}

),

final as (

    select
        rcb.recipe_ingredient_id,
        rcb.recipe_id,
        r.recipe_name,
        r.menu_item_id,
        r.is_active_recipe,
        rcb.ingredient_id,
        rcb.ingredient_name,
        rcb.ingredient_category,
        rcb.quantity,
        rcb.quantity_unit,
        rcb.ingredient_unit_cost,
        rcb.ingredient_line_cost,
        rcb.ingredient_line_cost * 1.0
            / nullif(sum(rcb.ingredient_line_cost) over (partition by rcb.recipe_id), 0)
            as cost_share_pct

    from recipe_cost_breakdown as rcb
    inner join recipes as r
        on rcb.recipe_id = r.recipe_id

)

select * from final
