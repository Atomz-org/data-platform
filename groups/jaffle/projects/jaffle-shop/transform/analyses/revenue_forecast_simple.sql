-- Analysis: Simple revenue trend extrapolation
-- Uses monthly revenue data to project next 3 months based on linear trend

with monthly_revenue as (
    select
        month_start,
        monthly_revenue,
        row_number() over (order by month_start) as month_num
    from {{ ref('exec_company_kpis_monthly') }}
),

trend as (
    select
        avg(monthly_revenue) as avg_revenue,
        regr_slope(monthly_revenue, month_num) as slope,
        regr_intercept(monthly_revenue, month_num) as intercept,
        max(month_num) as last_month_num,
        max(month_start) as last_month
    from monthly_revenue
)

select
    t.last_month as last_actual_month,
    round(t.avg_revenue, 2) as avg_monthly_revenue,
    round(t.slope, 2) as monthly_trend,
    round(t.intercept + t.slope * (t.last_month_num + 1), 2) as forecast_month_1,
    round(t.intercept + t.slope * (t.last_month_num + 2), 2) as forecast_month_2,
    round(t.intercept + t.slope * (t.last_month_num + 3), 2) as forecast_month_3
from trend t
