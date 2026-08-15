with

monthly_revenue as (

    select * from {{ ref('met_monthly_revenue_by_store') }}

),

growth as (

    select
        location_id,
        month_start,
        monthly_revenue,
        lag(monthly_revenue) over (partition by location_id order by month_start) as prev_month_revenue,
        round(
            (monthly_revenue - lag(monthly_revenue) over (partition by location_id order by month_start))
            * 100.0 / nullif(lag(monthly_revenue) over (partition by location_id order by month_start), 0), 2
        ) as mom_growth_pct

    from monthly_revenue

),

growth_trend as (

    select
        location_id,
        month_start,
        monthly_revenue,
        mom_growth_pct,
        avg(mom_growth_pct) over (
            partition by location_id
            order by month_start
            rows between 5 preceding and current row
        ) as rolling_6m_avg_growth,
        avg(mom_growth_pct) over (
            partition by location_id
            order by month_start
            rows between 11 preceding and current row
        ) as rolling_12m_avg_growth

    from growth
    where mom_growth_pct is not null

)

select
    location_id,
    month_start,
    monthly_revenue,
    mom_growth_pct,
    round(rolling_6m_avg_growth, 2) as rolling_6m_avg_growth,
    round(rolling_12m_avg_growth, 2) as rolling_12m_avg_growth,
    case
        when rolling_6m_avg_growth < rolling_12m_avg_growth - 3 then 'growth_slowdown_detected'
        when rolling_6m_avg_growth < 0 then 'declining'
        else 'stable_or_growing'
    end as competition_signal

from growth_trend
