with

recipe_costs as (

    select * from {{ ref('fct_recipe_costs') }}

),

recipe_total_cost as (

    select * from {{ ref('int_recipe_total_cost') }}

),

recipes as (

    select * from {{ ref('stg_recipes') }}

),

-- fct_recipe_costs has per-ingredient cost with cost_share_pct
-- int_recipe_total_cost has aggregated total cost per recipe
-- Compare current ingredient costs (int_recipe_total_cost) against recipe-level expected cost

recipe_expected_vs_actual as (

    select
        rc.recipe_id,
        rc.recipe_name,
        rc.menu_item_id,
        rc.is_active_recipe,
        rc.ingredient_id,
        rc.ingredient_name,
        rc.ingredient_category,
        rc.quantity,
        rc.quantity_unit,
        rc.ingredient_unit_cost,
        rc.ingredient_line_cost,
        rc.cost_share_pct

    from recipe_costs as rc

),

recipe_summary as (

    select
        recipe_id,
        recipe_name,
        menu_item_id,
        is_active_recipe,
        count(distinct ingredient_id) as ingredient_count,
        sum(ingredient_line_cost) as calculated_total_cost,
        max(ingredient_line_cost) as max_ingredient_cost,
        min(ingredient_line_cost) as min_ingredient_cost,
        max(ingredient_line_cost) - min(ingredient_line_cost) as ingredient_cost_spread

    from recipe_expected_vs_actual
    group by recipe_id, recipe_name, menu_item_id, is_active_recipe

),

final as (

    select
        rs.recipe_id,
        rs.recipe_name,
        rs.menu_item_id,
        rs.is_active_recipe,
        rs.ingredient_count,
        rs.calculated_total_cost,
        rtc.total_ingredient_cost as baseline_total_cost,
        rs.calculated_total_cost - rtc.total_ingredient_cost as cost_variance,
        case
            when rtc.total_ingredient_cost > 0
            then (rs.calculated_total_cost - rtc.total_ingredient_cost)
                 / rtc.total_ingredient_cost * 100
            else null
        end as cost_variance_pct,
        rs.max_ingredient_cost,
        rs.min_ingredient_cost,
        rs.ingredient_cost_spread,
        case
            when abs(rs.calculated_total_cost - rtc.total_ingredient_cost)
                 / nullif(rtc.total_ingredient_cost, 0) * 100 > 10
            then 'high_variance'
            when abs(rs.calculated_total_cost - rtc.total_ingredient_cost)
                 / nullif(rtc.total_ingredient_cost, 0) * 100 > 5
            then 'moderate_variance'
            else 'within_tolerance'
        end as variance_status

    from recipe_summary as rs
    inner join recipe_total_cost as rtc
        on rs.recipe_id = rtc.recipe_id

)

select * from final
