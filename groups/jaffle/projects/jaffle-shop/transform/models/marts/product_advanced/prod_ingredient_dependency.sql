with

ri as (
    select * from {{ ref('stg_recipe_ingredients') }}
),

i as (
    select * from {{ ref('stg_ingredients') }}
),

recipe_ingredients as (

    select
        ri.recipe_id,
        ri.ingredient_id,
        i.ingredient_name,
        i.ingredient_category
    from ri
    inner join i
        on ri.ingredient_id = i.ingredient_id

),

ingredient_product_count as (

    select
        ingredient_id,
        ingredient_name,
        ingredient_category,
        count(distinct recipe_id) as products_using,
        cast(count(distinct recipe_id) as {{ dbt.type_float() }})
            / nullif((select count(distinct recipe_id) from {{ ref('stg_recipe_ingredients') }}), 0) * 100
            as pct_of_products
    from recipe_ingredients
    group by 1, 2, 3

),

final as (

    select
        ingredient_id,
        ingredient_name,
        ingredient_category,
        products_using,
        pct_of_products,
        case
            when pct_of_products > 50 then 'critical_dependency'
            when pct_of_products > 25 then 'high_dependency'
            when pct_of_products > 10 then 'moderate_dependency'
            else 'low_dependency'
        end as dependency_level,
        rank() over (order by products_using desc) as dependency_rank
    from ingredient_product_count

)

select * from final
