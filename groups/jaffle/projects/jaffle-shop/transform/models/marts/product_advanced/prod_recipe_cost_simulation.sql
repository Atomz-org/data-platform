with

recipe_costs as (
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

margins as (
    select
        menu_item_id,
        menu_item_price,
        gross_margin,
        gross_margin_pct
    from {{ ref('int_menu_item_margin') }}
),

simulated as (
    select
        r.recipe_id,
        r.recipe_name,
        r.menu_item_id,
        m.menu_item_price,
        m.gross_margin as current_margin,
        m.gross_margin_pct as current_margin_pct,
        sum(rc.ingredient_line_cost) as current_total_cost,
        sum(rc.ingredient_line_cost * 1.10) as simulated_cost_10pct_increase,
        m.menu_item_price - sum(rc.ingredient_line_cost * 1.10) as simulated_margin_10pct,
        case
            when m.menu_item_price > 0
            then (m.menu_item_price - sum(rc.ingredient_line_cost * 1.10)) / m.menu_item_price * 100
            else 0
        end as simulated_margin_pct_10pct,
        sum(rc.ingredient_line_cost * 0.10) as additional_cost_from_increase
    from recipe_costs as rc
    inner join recipes as r on rc.recipe_id = r.recipe_id
    left join margins as m on r.menu_item_id = m.menu_item_id
    group by 1, 2, 3, 4, 5, 6
),

final as (
    select
        *,
        case
            when simulated_margin_pct_10pct < 50 then 'margin_at_risk'
            when simulated_margin_pct_10pct < current_margin_pct - 5 then 'significant_impact'
            else 'manageable_impact'
        end as cost_impact_severity
    from simulated
)

select * from final
