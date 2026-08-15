with

daily_revenue as (

    select
        revenue_date,
        location_id,
        total_revenue
    from {{ ref('met_daily_revenue_by_store') }}

),

trended as (

    select
        revenue_date,
        location_id,
        total_revenue,
        avg(total_revenue) over (
            partition by location_id
            order by revenue_date
            rows between 6 preceding and current row
        ) as revenue_7d_ma,
        total_revenue - avg(total_revenue) over (
            partition by location_id
            order by revenue_date
            rows between 6 preceding and current row
        ) as deviation_from_7d_ma,
        case
            when total_revenue > avg(total_revenue) over (
                partition by location_id
                order by revenue_date
                rows between 6 preceding and current row
            ) * 1.2 then 'spike'
            when total_revenue < avg(total_revenue) over (
                partition by location_id
                order by revenue_date
                rows between 6 preceding and current row
            ) * 0.8 then 'dip'
            else 'normal'
        end as anomaly_flag
    from daily_revenue

)

select * from trended
