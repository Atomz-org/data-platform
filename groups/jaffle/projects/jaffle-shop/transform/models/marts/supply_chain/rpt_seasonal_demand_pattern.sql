with

demand_forecast as (

    select * from {{ ref('int_ingredient_demand_forecast') }}

),

monthly_demand as (

    select
        product_id,
        supply_id,
        supply_name,
        {{ dbt.date_trunc('month', 'demand_week') }} as demand_month,
        extract(month from demand_week) as month_of_year,
        sum(units_ordered) as total_units,
        sum(total_ingredient_cost) as total_cost,
        avg(forecast_units_4wk_avg) as avg_forecasted_units

    from demand_forecast

    group by
        product_id,
        supply_id,
        supply_name,
        {{ dbt.date_trunc('month', 'demand_week') }},
        extract(month from demand_week)

),

seasonal_stats as (

    select
        product_id,
        supply_id,
        supply_name,
        month_of_year,
        avg(total_units) as avg_monthly_units,
        avg(total_cost) as avg_monthly_cost,
        count(distinct demand_month) as months_of_data

    from monthly_demand

    group by
        product_id,
        supply_id,
        supply_name,
        month_of_year

),

with_index as (

    select
        seasonal_stats.*,
        avg(avg_monthly_units) over (
            partition by product_id, supply_id
        ) as overall_avg_units,
        case
            when avg(avg_monthly_units) over (
                partition by product_id, supply_id
            ) > 0
                then seasonal_stats.avg_monthly_units * 1.0
                    / avg(avg_monthly_units) over (
                        partition by product_id, supply_id
                    )
            else null
        end as seasonality_index

    from seasonal_stats

)

select * from with_index
