with

inventory as (

    select
        product_id,
        location_id,
        current_quantity
    from {{ ref('int_inventory_current_level') }}

),

ingredients as (

    select
        ingredient_id,
        ingredient_name,
        is_perishable,
        ingredient_category
    from {{ ref('stg_ingredients') }}
    where is_perishable = true

),

depletion as (

    select
        product_id,
        location_id,
        daily_depletion_rate
    from {{ ref('int_stock_depletion_rate') }}

),

final as (

    select
        inv.product_id,
        inv.location_id,
        ing.ingredient_name,
        ing.ingredient_category,
        inv.current_quantity,
        coalesce(dep.daily_depletion_rate, 0) as daily_depletion_rate,
        case
            when coalesce(dep.daily_depletion_rate, 0) > 0
            then inv.current_quantity / dep.daily_depletion_rate
            else null
        end as estimated_days_supply,
        case
            when coalesce(dep.daily_depletion_rate, 0) > 0
                and inv.current_quantity / dep.daily_depletion_rate > 7
            then 'high_risk'
            when coalesce(dep.daily_depletion_rate, 0) > 0
                and inv.current_quantity / dep.daily_depletion_rate > 3
            then 'moderate_risk'
            else 'low_risk'
        end as spoilage_risk
    from inventory as inv
    inner join ingredients as ing
        on inv.product_id = ing.ingredient_id
    left join depletion as dep
        on inv.product_id = dep.product_id
        and inv.location_id = dep.location_id

)

select * from final
