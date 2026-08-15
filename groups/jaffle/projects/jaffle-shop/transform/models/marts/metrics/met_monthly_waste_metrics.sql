with

daily_waste as (

    select * from {{ ref('met_daily_waste_metrics') }}

),

monthly_revenue as (

    select * from {{ ref('met_monthly_revenue_by_store') }}

),

monthly_waste as (

    select
        {{ dbt.date_trunc('month', 'waste_date') }} as month_start,
        location_id,
        location_name,
        sum(waste_events) as monthly_waste_events,
        sum(total_quantity_wasted) as monthly_quantity_wasted,
        sum(total_waste_cost) as monthly_waste_cost,
        avg(distinct_products_wasted) as avg_daily_products_wasted

    from daily_waste
    group by 1, 2, 3

),

with_revenue as (

    select
        mw.month_start,
        mw.location_id,
        mw.location_name,
        mw.monthly_waste_events,
        mw.monthly_quantity_wasted,
        mw.monthly_waste_cost,
        mw.avg_daily_products_wasted,
        coalesce(mr.monthly_revenue, 0) as monthly_revenue,
        case
            when coalesce(mr.monthly_revenue, 0) > 0
            then mw.monthly_waste_cost * 100.0 / mr.monthly_revenue
            else null
        end as waste_to_revenue_pct,
        lag(mw.monthly_waste_cost) over (
            partition by mw.location_id order by mw.month_start
        ) as prev_month_waste_cost,
        case
            when lag(mw.monthly_waste_cost) over (
                partition by mw.location_id order by mw.month_start
            ) > 0
            then (mw.monthly_waste_cost - lag(mw.monthly_waste_cost) over (
                partition by mw.location_id order by mw.month_start
            )) * 1.0 / lag(mw.monthly_waste_cost) over (
                partition by mw.location_id order by mw.month_start
            )
        end as mom_waste_cost_change

    from monthly_waste as mw

    left join monthly_revenue as mr
        on mw.location_id = mr.location_id
        and mw.month_start = mr.month_start

)

select * from with_revenue
