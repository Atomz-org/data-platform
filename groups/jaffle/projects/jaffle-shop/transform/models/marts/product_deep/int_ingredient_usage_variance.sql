with

actual_usage as (

    select
        ingredient_id,
        order_date as usage_date,
        total_quantity_used as actual_units_used
    from {{ ref('int_ingredient_usage_daily') }}

),

recipe_costs as (

    select
        recipe_id,
        ingredient_id,
        quantity as expected_quantity_per_recipe
    from {{ ref('stg_recipe_ingredients') }}

),

menu_items as (

    select menu_item_id, product_id from {{ ref('stg_menu_items') }}

),

recipes as (

    select recipe_id, menu_item_id from {{ ref('stg_recipes') }} where is_active_recipe = true

),

daily_product_sales as (

    select
        product_id,
        sale_date,
        units_sold
    from {{ ref('int_product_sales_daily') }}

),

expected_usage as (

    select
        rc.ingredient_id,
        dps.sale_date as usage_date,
        sum(dps.units_sold * rc.expected_quantity_per_recipe) as expected_ingredient_usage
    from daily_product_sales as dps
    inner join menu_items as mi on dps.product_id = mi.product_id
    inner join recipes as r on mi.menu_item_id = r.menu_item_id
    inner join recipe_costs as rc on r.recipe_id = rc.recipe_id
    group by 1, 2

),

final as (

    select
        au.ingredient_id,
        au.usage_date,
        au.actual_units_used,
        coalesce(eu.expected_ingredient_usage, 0) as expected_ingredient_usage,
        au.actual_units_used - coalesce(eu.expected_ingredient_usage, 0) as usage_variance,
        case
            when coalesce(eu.expected_ingredient_usage, 0) > 0
                then round(cast(
                    (au.actual_units_used - eu.expected_ingredient_usage) * 100.0
                    / eu.expected_ingredient_usage
                as {{ dbt.type_float() }}), 2)
            else null
        end as variance_pct
    from actual_usage as au
    left join expected_usage as eu
        on au.ingredient_id = eu.ingredient_id
        and au.usage_date = eu.usage_date

)

select * from final
