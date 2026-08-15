with

ri as (
    select * from {{ ref('stg_recipe_ingredients') }}
),

i as (
    select * from {{ ref('stg_ingredients') }}
),

recipes as (
    select * from {{ ref('stg_recipes') }}
),

ingredients as (
    select
        ri.recipe_id,
        ri.ingredient_id,
        i.ingredient_name,
        ri.quantity as ingredient_quantity,
        ri.quantity_unit
    from ri
    inner join i on ri.ingredient_id = i.ingredient_id
),

final as (
    select
        r.recipe_id,
        r.menu_item_id,
        r.recipe_name,
        ing.ingredient_id,
        ing.ingredient_name,
        ing.ingredient_quantity,
        ing.quantity_unit
    from recipes as r
    inner join ingredients as ing on r.recipe_id = ing.recipe_id
)

select * from final
