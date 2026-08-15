with

labor_demand as (

    select * from {{ ref('int_store_labor_demand') }}

),

orders as (

    select * from {{ ref('stg_orders') }}

),

monthly_demand as (

    select
        location_id,
        {{ dbt.date_trunc('month', 'ordered_at') }} as order_month,
        extract(month from ordered_at) as month_number,
        count(*) as total_orders,
        sum(order_total) as total_revenue

    from orders
    group by
        location_id,
        {{ dbt.date_trunc('month', 'ordered_at') }},
        extract(month from ordered_at)

),

monthly_averages as (

    select
        location_id,
        month_number,
        avg(total_orders) as avg_monthly_orders,
        avg(total_revenue) as avg_monthly_revenue,
        count(*) as months_of_data

    from monthly_demand
    group by
        location_id,
        month_number

),

overall_avg as (

    select
        location_id,
        avg(total_orders) as overall_avg_orders

    from monthly_demand
    group by location_id

),

seasonal_index as (

    select
        monthly_averages.location_id,
        monthly_averages.month_number,
        case monthly_averages.month_number
            when 1 then 'January'
            when 2 then 'February'
            when 3 then 'March'
            when 4 then 'April'
            when 5 then 'May'
            when 6 then 'June'
            when 7 then 'July'
            when 8 then 'August'
            when 9 then 'September'
            when 10 then 'October'
            when 11 then 'November'
            when 12 then 'December'
        end as month_name,
        case
            when monthly_averages.month_number in (12, 1, 2) then 'winter'
            when monthly_averages.month_number in (3, 4, 5) then 'spring'
            when monthly_averages.month_number in (6, 7, 8) then 'summer'
            else 'fall'
        end as season,
        monthly_averages.avg_monthly_orders,
        monthly_averages.avg_monthly_revenue,
        monthly_averages.months_of_data,
        case
            when overall_avg.overall_avg_orders > 0
                then round(
                    (monthly_averages.avg_monthly_orders * 100.0
                    / overall_avg.overall_avg_orders), 1
                )
            else null
        end as demand_index,
        case
            when monthly_averages.avg_monthly_orders > overall_avg.overall_avg_orders * 1.15
                then 'high_demand'
            when monthly_averages.avg_monthly_orders < overall_avg.overall_avg_orders * 0.85
                then 'low_demand'
            else 'normal_demand'
        end as demand_classification

    from monthly_averages
    inner join overall_avg
        on monthly_averages.location_id = overall_avg.location_id

),

with_staffing_recommendation as (

    select
        seasonal_index.location_id,
        seasonal_index.month_number,
        seasonal_index.month_name,
        seasonal_index.season,
        round(seasonal_index.avg_monthly_orders, 0) as avg_monthly_orders,
        round(seasonal_index.avg_monthly_revenue, 2) as avg_monthly_revenue,
        seasonal_index.demand_index,
        seasonal_index.demand_classification,
        labor_demand.avg_labor_hours as current_avg_labor_hours,
        labor_demand.avg_staff_count as current_avg_staff,
        case
            when seasonal_index.demand_classification = 'high_demand'
                then round(coalesce(labor_demand.avg_staff_count, 0) * 1.2, 0)
            when seasonal_index.demand_classification = 'low_demand'
                then round(coalesce(labor_demand.avg_staff_count, 0) * 0.85, 0)
            else round(coalesce(labor_demand.avg_staff_count, 0), 0)
        end as recommended_staff_count

    from seasonal_index
    left join labor_demand
        on seasonal_index.location_id = labor_demand.location_id

)

select * from with_staffing_recommendation
