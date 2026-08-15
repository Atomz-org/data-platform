with

expense_ratio as (

    select
        location_id,
        expense_month,
        category_name,
        expense_to_revenue_pct
    from {{ ref('int_expense_by_revenue_ratio') }}
    where expense_to_revenue_pct > 15

),

waste_cost as (

    select
        location_id,
        {{ dbt.date_trunc('month', 'wasted_at') }} as waste_month,
        sum(cost_of_waste) as monthly_waste_cost
    from {{ ref('stg_waste_logs') }}
    group by 1, 2

),

overtime as (

    select
        location_id,
        {{ dbt.date_trunc('month', 'week_start') }} as overtime_month,
        sum(weekly_daily_overtime_hours) as monthly_overtime_hours
    from {{ ref('int_overtime_hours') }}
    group by 1, 2

),

high_expense_flags as (

    select
        location_id,
        expense_month as flag_month,
        'high_expense_ratio' as optimization_area,
        category_name as detail,
        expense_to_revenue_pct as metric_value
    from expense_ratio

),

high_waste_flags as (

    select
        location_id,
        waste_month as flag_month,
        'excessive_waste' as optimization_area,
        'waste_cost' as detail,
        monthly_waste_cost as metric_value
    from waste_cost
    where monthly_waste_cost > 500

),

high_overtime_flags as (

    select
        location_id,
        overtime_month as flag_month,
        'high_overtime' as optimization_area,
        'overtime_hours' as detail,
        monthly_overtime_hours as metric_value
    from overtime
    where monthly_overtime_hours > 100

),

final as (

    select * from high_expense_flags
    union all
    select * from high_waste_flags
    union all
    select * from high_overtime_flags

)

select * from final
