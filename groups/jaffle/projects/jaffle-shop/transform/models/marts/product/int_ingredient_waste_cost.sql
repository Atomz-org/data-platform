with

ingredient_usage_daily as (

    select * from {{ ref('int_ingredient_usage_daily') }}

),

ingredient_cost_trend as (

    select * from {{ ref('int_ingredient_cost_trend') }}

),

ingredients as (

    select * from {{ ref('stg_ingredients') }}

),

monthly_usage as (

    select
        ingredient_id,
        {{ dbt.date_trunc('month', 'order_date') }} as usage_month,
        sum(total_quantity_used) as total_quantity_used,
        avg(total_quantity_used) as avg_daily_usage,
        max(total_quantity_used) as peak_daily_usage,
        count(distinct order_date) as active_days

    from ingredient_usage_daily
    group by ingredient_id, {{ dbt.date_trunc('month', 'order_date') }}

),

waste_estimate as (

    select
        mu.ingredient_id,
        i.ingredient_name,
        i.ingredient_category,
        i.is_perishable,
        mu.usage_month,
        mu.total_quantity_used,
        mu.avg_daily_usage,
        mu.peak_daily_usage,
        mu.active_days,
        -- Estimate waste as the gap between peak-based purchasing and actual usage
        -- Assume purchasing is based on peak daily usage across the month
        (mu.peak_daily_usage * mu.active_days) - mu.total_quantity_used as estimated_waste_quantity,
        ict.avg_unit_cost,
        ((mu.peak_daily_usage * mu.active_days) - mu.total_quantity_used)
            * coalesce(ict.avg_unit_cost, 0) as estimated_waste_cost,
        case
            when mu.total_quantity_used > 0
            then ((mu.peak_daily_usage * mu.active_days) - mu.total_quantity_used)
                 * 1.0 / (mu.peak_daily_usage * mu.active_days) * 100
            else 0
        end as estimated_waste_pct

    from monthly_usage as mu
    inner join ingredients as i
        on mu.ingredient_id = i.ingredient_id
    left join ingredient_cost_trend as ict
        on mu.ingredient_id = ict.ingredient_id
        and mu.usage_month = ict.price_month

)

select * from waste_estimate
