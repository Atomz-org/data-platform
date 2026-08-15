with

cost_trend as (

    select
        ingredient_id,
        price_month,
        avg_unit_cost,
        mom_cost_change_pct
    from {{ ref('int_ingredient_cost_trend') }}

),

ingredients as (

    select ingredient_id, ingredient_name, ingredient_category
    from {{ ref('stg_ingredients') }}

),

volatility as (

    select
        ct.ingredient_id,
        i.ingredient_name,
        i.ingredient_category,
        avg(ct.avg_unit_cost) as mean_cost,
        max(ct.avg_unit_cost) - min(ct.avg_unit_cost) as cost_range,
        case
            when avg(ct.avg_unit_cost) > 0
            then (max(ct.avg_unit_cost) - min(ct.avg_unit_cost)) / avg(ct.avg_unit_cost)
            else 0
        end as volatility_ratio,
        avg(ct.mom_cost_change_pct) as avg_monthly_change,
        count(case when ct.mom_cost_change_pct > 5 then 1 end) as months_with_5pct_increase
    from cost_trend as ct
    inner join ingredients as i on ct.ingredient_id = i.ingredient_id
    group by 1, 2, 3

),

final as (

    select
        ingredient_id,
        ingredient_name,
        ingredient_category,
        mean_cost,
        cost_range,
        volatility_ratio,
        avg_monthly_change,
        months_with_5pct_increase,
        case
            when volatility_ratio > 0.4 then 'hedge_immediately'
            when volatility_ratio > 0.2 then 'consider_hedging'
            when avg_monthly_change > 3 then 'monitor_closely'
            else 'no_action_needed'
        end as hedge_recommendation
    from volatility

)

select * from final
