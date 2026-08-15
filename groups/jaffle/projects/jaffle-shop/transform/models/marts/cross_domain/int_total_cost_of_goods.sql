with recipe_totals as (
    select * from {{ ref('int_recipe_total_cost') }}
),

recipes as (
    select * from {{ ref('stg_recipes') }}
),

menu_items as (
    select * from {{ ref('stg_menu_items') }}
),

recipe_costs as (
    select
        r.recipe_id,
        mi.product_id,
        rc.total_ingredient_cost as ingredient_cost_per_unit
    from recipe_totals as rc
    inner join recipes as r on rc.recipe_id = r.recipe_id
    inner join menu_items as mi on r.menu_item_id = mi.menu_item_id
),

supplies as (
    select * from {{ ref('stg_supplies') }}
),

supply_costs as (
    select
        product_id,
        sum(supply_cost) as total_supply_cost,
        count(distinct supply_id) as supply_count,
        avg(supply_cost) as avg_supply_cost_per_item
    from supplies
    group by product_id
)

select
    coalesce(cast(rc.product_id as {{ dbt.type_string() }}), cast(sc.product_id as {{ dbt.type_string() }})) as product_id,
    coalesce(rc.ingredient_cost_per_unit, 0) as ingredient_cost_per_unit,
    coalesce(sc.avg_supply_cost_per_item, 0) as supply_cost_per_unit,
    coalesce(rc.ingredient_cost_per_unit, 0)
        + coalesce(sc.avg_supply_cost_per_item, 0) as total_cogs_per_unit,
    sc.supply_count,
    case
        when coalesce(rc.ingredient_cost_per_unit, 0)
            + coalesce(sc.avg_supply_cost_per_item, 0) > 0
            then round(
                (cast(coalesce(rc.ingredient_cost_per_unit, 0) as {{ dbt.type_float() }})
                / (coalesce(rc.ingredient_cost_per_unit, 0) + coalesce(sc.avg_supply_cost_per_item, 0))
                * 100), 2
            )
        else 0
    end as ingredient_cost_share_pct
from recipe_costs as rc
full outer join supply_costs as sc
    on cast(rc.product_id as {{ dbt.type_string() }}) = cast(sc.product_id as {{ dbt.type_string() }})
