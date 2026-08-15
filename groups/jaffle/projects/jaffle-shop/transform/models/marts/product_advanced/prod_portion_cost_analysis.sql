with

recipe_cost_detail as (
    select
        recipe_id,
        ingredient_id,
        ingredient_name,
        ingredient_unit_cost,
        ingredient_line_cost
    from {{ ref('int_recipe_cost_breakdown') }}
),

recipes as (
    select recipe_id, recipe_name, menu_item_id
    from {{ ref('dim_recipes') }}
),

items as (
    select menu_item_id, menu_item_name, menu_item_price
    from {{ ref('dim_menu_items') }}
),

final as (
    select
        r.menu_item_id,
        mi.menu_item_name,
        mi.menu_item_price,
        rcd.recipe_id,
        rcd.ingredient_id,
        rcd.ingredient_name,
        rcd.ingredient_line_cost,
        sum(rcd.ingredient_line_cost) over (partition by rcd.recipe_id) as total_recipe_cost,
        case
            when mi.menu_item_price > 0
            then rcd.ingredient_line_cost / mi.menu_item_price * 100
            else 0
        end as ingredient_pct_of_price,
        rank() over (partition by rcd.recipe_id order by rcd.ingredient_line_cost desc) as cost_rank
    from recipe_cost_detail as rcd
    inner join recipes as r on rcd.recipe_id = r.recipe_id
    inner join items as mi on r.menu_item_id = mi.menu_item_id
)

select * from final
