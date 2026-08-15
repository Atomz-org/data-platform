with

ri as (
    select * from {{ ref('stg_recipe_ingredients') }}
),

recipe_ingredients as (

    select
        ri.recipe_id,
        count(distinct ri.ingredient_id) as ingredient_count
    from ri
    group by 1

),

recipes as (

    select recipe_id, recipe_name, menu_item_id
    from {{ ref('dim_recipes') }}

),

margins as (

    select menu_item_id, gross_margin, gross_margin_pct
    from {{ ref('int_menu_item_margin') }}

),

final as (

    select
        r.recipe_id,
        r.recipe_name,
        r.menu_item_id,
        ri.ingredient_count,
        coalesce(m.gross_margin, 0) as gross_margin,
        coalesce(m.gross_margin_pct, 0) as gross_margin_pct,
        case
            when ri.ingredient_count > 12 then 'strong_candidate'
            when ri.ingredient_count > 8 then 'moderate_candidate'
            else 'no_simplification_needed'
        end as simplification_recommendation,
        -- Estimated savings: 5% cost reduction per ingredient removed above 8
        case
            when ri.ingredient_count > 8
            then (ri.ingredient_count - 8) * 0.05 * coalesce(m.gross_margin, 0)
            else 0
        end as estimated_savings_per_unit
    from recipe_ingredients as ri
    inner join recipes as r on ri.recipe_id = r.recipe_id
    left join margins as m on r.menu_item_id = m.menu_item_id

)

select * from final
