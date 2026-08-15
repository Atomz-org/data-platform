with

demand_forecast as (

    select
        product_id,
        demand_week,
        forecast_units_4wk_avg
    from {{ ref('int_ingredient_demand_forecast') }}

),

monthly_sales as (

    select
        product_id,
        month_start,
        monthly_units,
        monthly_revenue
    from {{ ref('met_monthly_product_sales') }}

),

seasonal_index as (

    select
        product_id,
        extract(month from month_start) as calendar_month,
        avg(monthly_units) as avg_monthly_qty,
        avg(avg(monthly_units)) over (partition by product_id) as overall_avg_qty
    from monthly_sales
    group by 1, 2

),

final as (

    select
        si.product_id,
        si.calendar_month,
        si.avg_monthly_qty,
        si.overall_avg_qty,
        case
            when si.overall_avg_qty > 0
            then si.avg_monthly_qty / si.overall_avg_qty
            else 1
        end as seasonal_factor,
        -- Recommended stock = avg demand × seasonal factor × safety buffer (1.2)
        si.avg_monthly_qty
            * (case when si.overall_avg_qty > 0
                    then si.avg_monthly_qty / si.overall_avg_qty
                    else 1 end)
            * 1.2 as recommended_monthly_stock,
        case
            when si.avg_monthly_qty > si.overall_avg_qty * 1.15 then 'peak_demand'
            when si.avg_monthly_qty < si.overall_avg_qty * 0.85 then 'low_demand'
            else 'normal_demand'
        end as demand_season
    from seasonal_index as si

)

select * from final
