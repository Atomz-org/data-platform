with

ingredient_cost_trend as (

    select * from {{ ref('int_ingredient_cost_trend') }}

),

recipe_cost_breakdown as (

    select * from {{ ref('int_recipe_cost_breakdown') }}

),

recipes as (

    select * from {{ ref('stg_recipes') }}

),

menu_item_margin as (

    select * from {{ ref('int_menu_item_margin') }}

),

-- Get the cost change per ingredient per month
ingredient_change as (

    select
        ingredient_id,
        price_month,
        avg_unit_cost,
        prev_month_avg_cost,
        mom_cost_change_pct,
        avg_unit_cost - coalesce(prev_month_avg_cost, avg_unit_cost) as unit_cost_change

    from ingredient_cost_trend
    where prev_month_avg_cost is not null

),

-- Map ingredient cost changes to recipe cost impact
recipe_impact as (

    select
        ic.price_month,
        rcb.recipe_id,
        r.recipe_name,
        r.menu_item_id,
        rcb.ingredient_id,
        rcb.ingredient_name,
        rcb.ingredient_category,
        rcb.quantity,
        ic.avg_unit_cost as current_unit_cost,
        ic.prev_month_avg_cost,
        ic.unit_cost_change,
        ic.mom_cost_change_pct,
        rcb.quantity * ic.unit_cost_change as ingredient_cost_impact

    from recipe_cost_breakdown as rcb
    inner join ingredient_change as ic
        on rcb.ingredient_id = ic.ingredient_id
    inner join recipes as r
        on rcb.recipe_id = r.recipe_id
        and r.is_active_recipe = true

),

-- Summarize impact per menu item per month
menu_item_impact as (

    select
        ri.price_month,
        ri.menu_item_id,
        mim.menu_item_name,
        mim.menu_item_price,
        mim.gross_margin,
        mim.gross_margin_pct,
        sum(ri.ingredient_cost_impact) as total_cost_impact,
        count(distinct ri.ingredient_id) as ingredients_with_change,
        mim.gross_margin - sum(ri.ingredient_cost_impact) as adjusted_margin,
        case
            when mim.menu_item_price > 0
            then (mim.gross_margin - sum(ri.ingredient_cost_impact))
                 / mim.menu_item_price * 100
            else 0
        end as adjusted_margin_pct

    from recipe_impact as ri
    inner join menu_item_margin as mim
        on ri.menu_item_id = mim.menu_item_id
    group by
        ri.price_month,
        ri.menu_item_id,
        mim.menu_item_name,
        mim.menu_item_price,
        mim.gross_margin,
        mim.gross_margin_pct

)

select * from menu_item_impact
