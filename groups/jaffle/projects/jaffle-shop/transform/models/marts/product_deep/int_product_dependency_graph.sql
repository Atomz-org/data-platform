with

recipe_ingredients as (

    select * from {{ ref('stg_recipe_ingredients') }}

),

recipes as (

    select
        recipe_id,
        menu_item_id
    from {{ ref('stg_recipes') }}

),

menu_items as (

    select
        menu_item_id,
        product_id
    from {{ ref('stg_menu_items') }}

),

product_ingredients as (

    select distinct
        mi.product_id,
        ri.ingredient_id
    from recipe_ingredients as ri
    inner join recipes as r
        on ri.recipe_id = r.recipe_id
    inner join menu_items as mi
        on r.menu_item_id = mi.menu_item_id

),

product_pairs as (

    select
        a.product_id as product_a,
        b.product_id as product_b,
        count(distinct a.ingredient_id) as shared_ingredient_count
    from product_ingredients as a
    inner join product_ingredients as b
        on a.ingredient_id = b.ingredient_id
        and a.product_id < b.product_id
    group by 1, 2

),

product_total_ingredients as (

    select
        product_id,
        count(distinct ingredient_id) as total_ingredients
    from product_ingredients
    group by 1

),

final as (

    select
        pp.product_a,
        pp.product_b,
        pp.shared_ingredient_count,
        pa.total_ingredients as product_a_ingredients,
        pb.total_ingredients as product_b_ingredients,
        case
            when {{ sf_least(["pa.total_ingredients", "pb.total_ingredients"]) }} > 0
                then round(cast(
                    pp.shared_ingredient_count * 100.0
                    / {{ sf_least(["pa.total_ingredients", "pb.total_ingredients"]) }}
                as {{ dbt.type_float() }}), 2)
            else 0
        end as ingredient_overlap_pct
    from product_pairs as pp
    left join product_total_ingredients as pa
        on pp.product_a = pa.product_id
    left join product_total_ingredients as pb
        on pp.product_b = pb.product_id

)

select * from final
