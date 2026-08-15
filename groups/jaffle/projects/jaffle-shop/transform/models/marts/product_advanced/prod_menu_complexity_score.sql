with

ri as (
    select * from {{ ref('stg_recipe_ingredients') }}
),

r as (
    select * from {{ ref('dim_recipes') }}
),

i as (
    select * from {{ ref('stg_ingredients') }}
),

menu_items as (

    select
        menu_item_id,
        menu_item_name,
        category_name
    from {{ ref('dim_menu_items') }}

),

recipe_complexity as (

    select
        r.menu_item_id,
        count(distinct ri.ingredient_id) as ingredient_count,
        count(distinct i.ingredient_category) as category_count
    from ri
    inner join r on ri.recipe_id = r.recipe_id
    inner join i on ri.ingredient_id = i.ingredient_id
    group by 1

),

store_menu_size as (

    select
        count(distinct menu_item_id) as total_menu_items,
        count(distinct category_name) as total_categories
    from menu_items

),

final as (

    select
        mi.menu_item_id,
        mi.menu_item_name,
        mi.category_name,
        coalesce(rc.ingredient_count, 0) as ingredient_count,
        coalesce(rc.category_count, 0) as ingredient_category_count,
        sms.total_menu_items,
        sms.total_categories,
        -- Complexity score: more ingredients = more complex
        case
            when coalesce(rc.ingredient_count, 0) > 10 then 'highly_complex'
            when coalesce(rc.ingredient_count, 0) > 5 then 'moderately_complex'
            else 'simple'
        end as item_complexity,
        coalesce(rc.ingredient_count, 0) as complexity_score
    from menu_items as mi
    left join recipe_complexity as rc on mi.menu_item_id = rc.menu_item_id
    cross join store_menu_size as sms

)

select * from final
