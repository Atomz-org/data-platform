with

daily_usage as (

    select
        ingredient_id,
        avg(total_quantity_used) as avg_daily_usage
    from {{ ref('int_ingredient_usage_daily') }}
    group by 1

),

prices as (

    select
        ingredient_id,
        avg(unit_cost) as avg_unit_cost
    from {{ ref('stg_ingredient_prices') }}
    group by 1

),

ingredients as (

    select ingredient_id, ingredient_name
    from {{ ref('stg_ingredients') }}

),

final as (

    select
        du.ingredient_id,
        i.ingredient_name,
        du.avg_daily_usage,
        du.avg_daily_usage * 365 as annual_demand,
        p.avg_unit_cost,
        -- Assume ordering cost = $25 per order, holding cost = 20% of unit cost per year
        25.0 as ordering_cost_per_order,
        p.avg_unit_cost * 0.20 as annual_holding_cost_per_unit,
        -- EOQ = sqrt(2 * D * S / H)
        case
            when p.avg_unit_cost * 0.20 > 0
            then sqrt(2 * du.avg_daily_usage * 365 * 25.0 / (p.avg_unit_cost * 0.20))
            else null
        end as economic_order_quantity,
        case
            when du.avg_daily_usage > 0 and p.avg_unit_cost * 0.20 > 0
            then (du.avg_daily_usage * 365)
                / sqrt(2 * du.avg_daily_usage * 365 * 25.0 / (p.avg_unit_cost * 0.20))
            else null
        end as orders_per_year
    from daily_usage as du
    inner join prices as p on du.ingredient_id = p.ingredient_id
    inner join ingredients as i on du.ingredient_id = i.ingredient_id

)

select * from final
