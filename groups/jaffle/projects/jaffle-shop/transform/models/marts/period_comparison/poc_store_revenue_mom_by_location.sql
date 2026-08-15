with

monthly_store as (
    select
        month_start,
        location_id,
        monthly_revenue
    from {{ ref('met_monthly_revenue_by_store') }}
),

fleet_avg as (
    select
        month_start,
        avg(monthly_revenue) as fleet_avg_revenue
    from monthly_store
    group by 1
),

compared as (
    select
        ms.month_start,
        ms.location_id,
        ms.monthly_revenue as current_revenue,
        lag(ms.monthly_revenue) over (partition by ms.location_id order by ms.month_start) as prior_month_revenue,
        round((ms.monthly_revenue - lag(ms.monthly_revenue) over (partition by ms.location_id order by ms.month_start)) * 100.0
            / nullif(lag(ms.monthly_revenue) over (partition by ms.location_id order by ms.month_start), 0), 2) as mom_change_pct,
        fa.fleet_avg_revenue,
        round(ms.monthly_revenue * 100.0 / nullif(fa.fleet_avg_revenue, 0), 2) as pct_of_fleet_avg
    from monthly_store as ms
    inner join fleet_avg as fa on ms.month_start = fa.month_start
)

select * from compared
