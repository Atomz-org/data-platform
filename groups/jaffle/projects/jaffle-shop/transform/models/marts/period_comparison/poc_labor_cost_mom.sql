with

monthly_labor as (
    select
        month_start,
        location_id,
        monthly_labor_cost,
        monthly_labor_hours
    from {{ ref('met_monthly_labor_metrics') }}
),

compared as (
    select
        month_start,
        location_id,
        monthly_labor_cost as current_cost,
        lag(monthly_labor_cost) over (partition by location_id order by month_start) as prior_month_cost,
        monthly_labor_hours as current_hours,
        lag(monthly_labor_hours) over (partition by location_id order by month_start) as prior_month_hours,
        round(((monthly_labor_cost - lag(monthly_labor_cost) over (partition by location_id order by month_start))) * 100.0
            / nullif(lag(monthly_labor_cost) over (partition by location_id order by month_start), 0), 2) as labor_cost_mom_pct,
        round(((monthly_labor_hours - lag(monthly_labor_hours) over (partition by location_id order by month_start))) * 100.0
            / nullif(lag(monthly_labor_hours) over (partition by location_id order by month_start), 0), 2) as hours_mom_pct
    from monthly_labor
)

select * from compared
