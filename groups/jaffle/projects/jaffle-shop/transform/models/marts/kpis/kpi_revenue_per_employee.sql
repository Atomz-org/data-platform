with monthly_rev as (
    select month_start, location_id, monthly_revenue
    from {{ ref('met_monthly_revenue_by_store') }}
),
monthly_emp as (
    select 
        {{ dbt.date_trunc('month', 'work_date') }} as month_start,
        location_id, 
        avg(employee_count) as avg_employees
    from {{ ref('met_daily_labor_metrics') }}
    group by 1, 2
),
final as (
    select
        r.month_start,
        r.location_id,
        r.monthly_revenue,
        coalesce(round(e.avg_employees, 0), 0) as avg_employees,
        round(r.monthly_revenue * 1.0 / nullif(e.avg_employees, 0), 2) as revenue_per_employee
    from monthly_rev as r
    left join monthly_emp as e on r.month_start = e.month_start and r.location_id = e.location_id
)
select * from final
