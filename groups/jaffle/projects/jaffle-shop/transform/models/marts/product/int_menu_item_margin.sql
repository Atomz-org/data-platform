with

menu_item_enriched as (

    select * from {{ ref('int_menu_item_enriched') }}

),

recipe_total_cost as (

    select * from {{ ref('int_recipe_total_cost') }}

),

recipes as (

    select * from {{ ref('stg_recipes') }}

),

menu_with_cost as (

    select
        mie.menu_item_id,
        mie.menu_item_name,
        mie.menu_item_price,
        mie.category_name,
        mie.product_type,
        mie.is_available,
        r.recipe_id,
        rtc.total_ingredient_cost,
        rtc.ingredient_count,
        mie.menu_item_price - coalesce(rtc.total_ingredient_cost, 0) as gross_margin,
        case
            when mie.menu_item_price > 0
            then (mie.menu_item_price - coalesce(rtc.total_ingredient_cost, 0))
                 / mie.menu_item_price * 100
            else 0
        end as gross_margin_pct

    from menu_item_enriched as mie
    left join recipes as r
        on mie.menu_item_id = r.menu_item_id
        and r.is_active_recipe = true
    left join recipe_total_cost as rtc
        on r.recipe_id = rtc.recipe_id

)

select * from menu_with_cost
