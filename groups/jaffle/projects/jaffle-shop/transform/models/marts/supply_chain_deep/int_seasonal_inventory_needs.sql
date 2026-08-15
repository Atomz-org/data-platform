with

demand_forecast as (

    select
        product_id,
        demand_week,
        forecast_units_4wk_avg as forecasted_quantity,
        units_ordered as quantity_volatility
    from {{ ref('int_ingredient_demand_forecast') }}

),

monthly_demand as (

    select
        product_id,
        {{ dbt.date_trunc('month', 'demand_week') }} as demand_month,
        sum(forecasted_quantity) as monthly_forecasted_demand,
        avg(quantity_volatility) as avg_volatility,
        sum(forecasted_quantity) + 2 * avg(coalesce(quantity_volatility, 0)) as safety_stock_demand
    from demand_forecast
    group by 1, 2

),

annual_avg as (

    select
        product_id,
        avg(monthly_forecasted_demand) as avg_monthly_demand
    from monthly_demand
    group by 1

),

final as (

    select
        md.product_id,
        md.demand_month,
        md.monthly_forecasted_demand,
        md.avg_volatility,
        md.safety_stock_demand,
        aa.avg_monthly_demand,
        case
            when aa.avg_monthly_demand > 0
                then round(cast(md.monthly_forecasted_demand / aa.avg_monthly_demand as {{ dbt.type_float() }}), 2)
            else null
        end as seasonal_index,
        case
            when aa.avg_monthly_demand > 0
                and md.monthly_forecasted_demand / aa.avg_monthly_demand > 1.2
                then 'peak'
            when aa.avg_monthly_demand > 0
                and md.monthly_forecasted_demand / aa.avg_monthly_demand < 0.8
                then 'low'
            else 'normal'
        end as season_classification
    from monthly_demand as md
    left join annual_avg as aa
        on md.product_id = aa.product_id

)

select * from final
