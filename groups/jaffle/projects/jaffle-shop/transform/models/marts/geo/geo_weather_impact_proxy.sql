with

monthly_revenue as (

    select * from {{ ref('met_monthly_revenue_by_store') }}

),

annual_avg as (

    select
        location_id,
        extract(year from month_start) as revenue_year,
        avg(monthly_revenue) as annual_avg_revenue

    from monthly_revenue
    group by location_id, extract(year from month_start)

),

monthly_with_avg as (

    select
        mr.location_id,
        mr.month_start,
        extract(month from mr.month_start) as calendar_month,
        extract(year from mr.month_start) as revenue_year,
        mr.monthly_revenue,
        aa.annual_avg_revenue,
        mr.monthly_revenue - aa.annual_avg_revenue as deviation_from_avg,
        round((mr.monthly_revenue - aa.annual_avg_revenue) * 100.0 / nullif(aa.annual_avg_revenue, 0), 2) as pct_deviation

    from monthly_revenue mr
    left join annual_avg aa
        on mr.location_id = aa.location_id
        and extract(year from mr.month_start) = aa.revenue_year

)

select
    location_id,
    calendar_month,
    round(avg(monthly_revenue), 2) as avg_monthly_revenue,
    round(avg(deviation_from_avg), 2) as avg_deviation_from_annual,
    round(avg(pct_deviation), 2) as avg_pct_deviation,
    case
        when avg(pct_deviation) > 10 then 'strong_positive_seasonality'
        when avg(pct_deviation) > 0 then 'mild_positive_seasonality'
        when avg(pct_deviation) > -10 then 'mild_negative_seasonality'
        else 'strong_negative_seasonality'
    end as seasonality_classification

from monthly_with_avg
group by location_id, calendar_month
