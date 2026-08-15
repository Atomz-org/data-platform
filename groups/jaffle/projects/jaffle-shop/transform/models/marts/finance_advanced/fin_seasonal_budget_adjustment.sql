with

monthly_rev as (

    select
        month_start,
        extract(month from month_start) as calendar_month,
        sum(monthly_revenue) as total_monthly_revenue
    from {{ ref('met_monthly_revenue_by_store') }}
    group by 1, 2

),

annual_avg as (

    select
        extract(year from month_start) as year_val,
        avg(total_monthly_revenue) as annual_avg_monthly_revenue
    from monthly_rev
    group by 1

),

seasonal_index as (

    select
        mr.calendar_month,
        avg(mr.total_monthly_revenue) as avg_month_revenue,
        avg(aa.annual_avg_monthly_revenue) as avg_annual_monthly,
        case
            when avg(aa.annual_avg_monthly_revenue) > 0
            then avg(mr.total_monthly_revenue) / avg(aa.annual_avg_monthly_revenue)
            else 1
        end as seasonal_factor
    from monthly_rev as mr
    inner join annual_avg as aa
        on extract(year from mr.month_start) = aa.year_val
    group by 1

),

final as (

    select
        calendar_month,
        avg_month_revenue,
        avg_annual_monthly,
        seasonal_factor,
        case
            when seasonal_factor > 1.15 then 'peak_season'
            when seasonal_factor < 0.85 then 'off_season'
            else 'normal_season'
        end as season_classification,
        -- Budget adjustment: multiply base budget by seasonal factor
        round(seasonal_factor, 3) as budget_multiplier
    from seasonal_index

)

select * from final
