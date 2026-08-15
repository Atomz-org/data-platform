with

ingredients as (

    select * from {{ ref('stg_ingredients') }}

),

ingredient_prices as (

    select * from {{ ref('stg_ingredient_prices') }}

),

current_prices as (

    select
        ingredient_id,
        unit_cost,
        row_number() over (
            partition by ingredient_id
            order by effective_from_date desc
        ) as price_recency_rank

    from ingredient_prices
    where effective_to_date is null
        or effective_to_date >= current_date

),

latest_price as (

    select
        ingredient_id,
        unit_cost as current_unit_cost

    from current_prices
    where price_recency_rank = 1

),

final as (

    select
        i.ingredient_id,
        i.ingredient_name,
        i.ingredient_category,
        i.default_unit,
        i.is_perishable,
        i.is_allergen,
        lp.current_unit_cost

    from ingredients as i
    left join latest_price as lp
        on i.ingredient_id = lp.ingredient_id

)

select * from final
