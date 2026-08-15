with

ri as (
    select * from {{ ref('stg_recipe_ingredients') }}
),

recipe_ingredients as (

    select ri.recipe_id, ri.ingredient_id
    from ri

),

ingredients as (

    select
        ingredient_id,
        ingredient_name,
        is_allergen,
        ingredient_category
    from {{ ref('stg_ingredients') }}

),

recipes as (

    select recipe_id, recipe_name, menu_item_id
    from {{ ref('dim_recipes') }}

),

items as (

    select menu_item_id, menu_item_name
    from {{ ref('dim_menu_items') }}

),

allergen_map as (

    select
        r.menu_item_id,
        mi.menu_item_name,
        r.recipe_name,
        count(case when i.is_allergen then 1 end) as allergen_ingredient_count,
        count(*) as total_ingredient_count,
        {{ sf_listagg("(case when i.is_allergen then i.ingredient_name end)", "', '") }} as allergen_list
    from recipe_ingredients as ri
    inner join ingredients as i on ri.ingredient_id = i.ingredient_id
    inner join recipes as r on ri.recipe_id = r.recipe_id
    inner join items as mi on r.menu_item_id = mi.menu_item_id
    group by 1, 2, 3

),

final as (

    select
        menu_item_id,
        menu_item_name,
        recipe_name,
        allergen_ingredient_count,
        total_ingredient_count,
        allergen_list,
        case
            when allergen_ingredient_count >= 3 then 'high_allergen_risk'
            when allergen_ingredient_count >= 1 then 'contains_allergens'
            else 'allergen_free'
        end as allergen_risk_level
    from allergen_map

)

select * from final
