with

product_sales as (
    select product_id, sale_date, units_sold
    from {{ ref('fct_product_sales') }}
),

recipe_ingredients_raw as (
    select * from {{ ref('stg_recipe_ingredients') }}
),

recipes as (
    select * from {{ ref('dim_recipes') }}
),

recipe_ingredients as (
    select
        ri.recipe_id,
        ri.ingredient_id,
        ri.quantity as recipe_quantity_per_unit,
        r.menu_item_id as product_id
    from recipe_ingredients_raw as ri
    inner join recipes as r on ri.recipe_id = r.recipe_id
),

ingredient_usage as (
    select
        ingredient_id,
        order_date,
        total_quantity_used
    from {{ ref('int_ingredient_usage_daily') }}
),

expected_vs_actual as (
    select
        ri.product_id,
        ri.ingredient_id,
        ri.recipe_quantity_per_unit,
        sum(ps.units_sold) as total_products_sold,
        sum(ps.units_sold) * ri.recipe_quantity_per_unit as expected_ingredient_usage,
        sum(iu.total_quantity_used) as actual_ingredient_usage
    from recipe_ingredients as ri
    inner join product_sales as ps on ri.product_id = ps.product_id
    left join ingredient_usage as iu
        on ri.ingredient_id = iu.ingredient_id
        and ps.sale_date = iu.order_date
    group by 1, 2, 3
),

final as (
    select
        product_id,
        ingredient_id,
        total_products_sold,
        expected_ingredient_usage,
        actual_ingredient_usage,
        case
            when expected_ingredient_usage > 0
            then actual_ingredient_usage * 1.0 / expected_ingredient_usage
            else null
        end as yield_ratio,
        case
            when actual_ingredient_usage > expected_ingredient_usage * 1.1 then 'over_usage'
            when actual_ingredient_usage < expected_ingredient_usage * 0.9 then 'under_usage'
            else 'on_target'
        end as yield_status
    from expected_vs_actual
)

select * from final
