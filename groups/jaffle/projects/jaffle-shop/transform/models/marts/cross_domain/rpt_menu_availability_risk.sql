with recipe_ingredients as (
    select
        menu_item_id as menu_product_id,
        ingredient_id,
        quantity,
        ingredient_unit_cost
    from {{ ref('fct_recipe_costs') }}
),

ingredient_supply as (
    select
        product_id as ingredient_product_id,
        total_stock_on_hand,
        weekly_demand_forecast as ingredient_weekly_demand,
        weeks_of_supply as ingredient_weeks_of_supply,
        stock_status as ingredient_stock_status
    from {{ ref('int_supply_capacity') }}
),

menu_ingredient_risk as (
    select
        ri.menu_product_id,
        ri.ingredient_id,
        ri.quantity,
        coalesce(is2.total_stock_on_hand, 0) as ingredient_stock,
        is2.ingredient_weeks_of_supply,
        is2.ingredient_stock_status,
        case
            when coalesce(is2.total_stock_on_hand, 0) <= 0 then 'unavailable'
            when is2.ingredient_stock_status in ('critical_low', 'out_of_stock') then 'at_risk'
            when is2.ingredient_stock_status = 'low' then 'watch'
            else 'available'
        end as ingredient_availability
    from recipe_ingredients as ri
    left join ingredient_supply as is2
        on ri.ingredient_id = is2.ingredient_product_id
),

menu_risk_summary as (
    select
        menu_product_id,
        count(distinct ingredient_id) as total_ingredients,
        count(case when ingredient_availability = 'unavailable' then 1 end) as unavailable_ingredients,
        count(case when ingredient_availability = 'at_risk' then 1 end) as at_risk_ingredients,
        count(case when ingredient_availability = 'watch' then 1 end) as watch_ingredients,
        min(ingredient_weeks_of_supply) as min_ingredient_weeks_supply
    from menu_ingredient_risk
    group by menu_product_id
),

product_info as (
    select product_id, product_name
    from {{ ref('products') }}
)

select
    mrs.menu_product_id as product_id,
    pi.product_name,
    mrs.total_ingredients,
    mrs.unavailable_ingredients,
    mrs.at_risk_ingredients,
    mrs.watch_ingredients,
    mrs.min_ingredient_weeks_supply,
    case
        when mrs.unavailable_ingredients > 0 then 'cannot_produce'
        when mrs.at_risk_ingredients > 0 then 'production_at_risk'
        when mrs.watch_ingredients > 0 then 'monitor'
        else 'fully_available'
    end as menu_availability_status,
    case
        when mrs.unavailable_ingredients > 0 then 1
        when mrs.at_risk_ingredients > 0 then 2
        when mrs.watch_ingredients > 0 then 3
        else 4
    end as risk_priority,
    round(
        (cast(mrs.unavailable_ingredients + mrs.at_risk_ingredients as {{ dbt.type_float() }})
        / nullif(mrs.total_ingredients, 0) * 100), 2
    ) as pct_ingredients_at_risk
from menu_risk_summary as mrs
left join product_info as pi
    on mrs.menu_product_id = pi.product_id
