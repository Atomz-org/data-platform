with

prices as (

    select
        ingredient_id,
        supplier_id,
        unit_cost,
        effective_from_date
    from {{ ref('stg_ingredient_prices') }}

),

ingredients as (

    select ingredient_id, ingredient_name, ingredient_category
    from {{ ref('stg_ingredients') }}

),

stats as (

    select
        p.ingredient_id,
        i.ingredient_name,
        i.ingredient_category,
        count(*) as price_observations,
        avg(p.unit_cost) as avg_price,
        min(p.unit_cost) as min_price,
        max(p.unit_cost) as max_price,
        max(p.unit_cost) - min(p.unit_cost) as price_range,
        case
            when avg(p.unit_cost) > 0
            then (max(p.unit_cost) - min(p.unit_cost)) / avg(p.unit_cost)
            else 0
        end as coefficient_of_variation_proxy
    from prices as p
    inner join ingredients as i on p.ingredient_id = i.ingredient_id
    group by 1, 2, 3

),

final as (

    select
        ingredient_id,
        ingredient_name,
        ingredient_category,
        price_observations,
        avg_price,
        min_price,
        max_price,
        price_range,
        coefficient_of_variation_proxy,
        case
            when coefficient_of_variation_proxy > 0.3 then 'high_volatility'
            when coefficient_of_variation_proxy > 0.15 then 'moderate_volatility'
            else 'low_volatility'
        end as volatility_category
    from stats

)

select * from final
