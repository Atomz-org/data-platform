with

recipes as (

    select * from {{ ref('stg_recipes') }}

),

recipe_total_cost as (

    select * from {{ ref('int_recipe_total_cost') }}

),

final as (

    select
        r.recipe_id,
        r.menu_item_id,
        r.recipe_name,
        r.recipe_description,
        r.serving_size,
        r.is_active_recipe,
        r.created_date,
        r.updated_date,
        rtc.ingredient_count,
        rtc.total_ingredient_cost,
        rtc.highest_ingredient_cost,
        rtc.lowest_ingredient_cost,
        case
            when r.serving_size > 0
            then rtc.total_ingredient_cost / r.serving_size
            else null
        end as cost_per_serving

    from recipes as r
    left join recipe_total_cost as rtc
        on r.recipe_id = rtc.recipe_id

)

select * from final
