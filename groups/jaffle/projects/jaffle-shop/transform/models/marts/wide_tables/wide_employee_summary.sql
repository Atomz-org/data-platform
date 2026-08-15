with

employees as (

    select * from {{ ref('dim_employees') }}

),

performance as (

    select * from {{ ref('scr_employee_performance') }}

),

training as (

    select
        employee_id,
        count(*) as courses_completed,
        avg(completion_score) as avg_training_score,
        min(completed_date) as first_training_date,
        max(completed_date) as last_training_date

    from {{ ref('stg_training_completions') }}
    group by employee_id

),

tenure as (

    select * from {{ ref('int_employee_tenure') }}

),

payroll as (

    select
        employee_id,
        sum(gross_pay) as total_gross_pay,
        sum(net_pay) as total_net_pay,
        avg(gross_pay) as avg_gross_pay,
        avg(effective_hourly_rate) as avg_hourly_rate,
        count(distinct pay_period_start) as pay_periods,
        min(pay_period_start) as first_pay_period,
        max(pay_period_end) as last_pay_period,
        sum(payroll_overtime_hours) as total_overtime_hours,
        sum(gross_pay) - sum(net_pay) as total_overtime_pay

    from {{ ref('fct_payroll') }}
    group by employee_id

),

shifts as (

    select
        employee_id,
        count(*) as total_shifts,
        sum(scheduled_hours) as total_shift_hours,
        avg(scheduled_hours) as avg_shift_hours,
        count(distinct location_id) as stores_worked_at,
        min(shift_date) as first_shift_date,
        max(shift_date) as last_shift_date

    from {{ ref('fct_shifts') }}
    group by employee_id

),

overtime as (

    select
        employee_id,
        sum(total_overtime_hours) as total_overtime_hours_calc,
        count(*) as overtime_weeks

    from {{ ref('int_overtime_hours') }}
    where total_overtime_hours > 0
    group by employee_id

),

locations as (

    select
        location_id,
        location_name
    from {{ ref('stg_locations') }}

),

departments as (

    select * from {{ ref('dim_departments') }}

)

select
    -- Identity
    e.employee_id,
    e.first_name,
    e.last_name,
    e.full_name as full_name,
    e.email,
    e.employment_status,
    e.is_active,

    -- Organization
    e.department_id,
    e.department_name,
    d.department_description,
    e.position_id,
    e.position_title,
    e.pay_grade,
    e.is_management,
    e.location_id as primary_store_id,
    loc.location_name as primary_store_name,

    -- Dates and tenure
    e.hire_date,
    e.termination_date,
    t.tenure_days,
    t.tenure_months,
    t.tenure_bucket,
    case
        when e.hire_date is not null
        then extract(year from e.hire_date)
        else null
    end as hire_year,
    case
        when e.hire_date is not null
        then extract(quarter from e.hire_date)
        else null
    end as hire_quarter,

    -- Pay
    e.min_hourly_rate,
    e.max_hourly_rate,
    coalesce(pay.avg_hourly_rate, 0) as actual_avg_hourly_rate,
    coalesce(pay.total_gross_pay, 0) as total_gross_pay,
    coalesce(pay.total_net_pay, 0) as total_net_pay,
    coalesce(pay.avg_gross_pay, 0) as avg_period_gross_pay,
    coalesce(pay.pay_periods, 0) as pay_periods_count,
    coalesce(pay.total_overtime_pay, 0) as total_overtime_pay,

    -- Shifts
    coalesce(sh.total_shifts, 0) as total_shifts,
    coalesce(sh.total_shift_hours, 0) as total_shift_hours,
    coalesce(sh.avg_shift_hours, 0) as avg_shift_hours,
    coalesce(sh.stores_worked_at, 0) as stores_worked_at,
    sh.first_shift_date,
    sh.last_shift_date,

    -- Overtime
    coalesce(ot.total_overtime_hours_calc, 0) as total_overtime_hours,
    coalesce(ot.overtime_weeks, 0) as overtime_weeks,
    case
        when coalesce(sh.total_shift_hours, 0) > 0
        then coalesce(ot.total_overtime_hours_calc, 0) * 100.0 / sh.total_shift_hours
        else 0
    end as overtime_pct,

    -- Performance
    p.performance_score,
    p.productivity_score,
    p.attendance_score,

    -- Training
    coalesce(tr.courses_completed, 0) as courses_completed,
    tr.avg_training_score,
    tr.first_training_date,
    tr.last_training_date,

    -- Derived
    case
        when coalesce(sh.total_shifts, 0) > 0 and t.tenure_months > 0
        then sh.total_shifts * 1.0 / t.tenure_months
        else 0
    end as shifts_per_month,
    case
        when p.performance_score >= 4.0 then 'top_performer'
        when p.performance_score >= 3.0 then 'meets_expectations'
        when p.performance_score >= 2.0 then 'needs_improvement'
        when p.performance_score is not null then 'underperforming'
        else 'not_rated'
    end as performance_tier

from employees as e
left join tenure as t on e.employee_id = t.employee_id
left join performance as p on e.employee_id = p.employee_id
left join training as tr on e.employee_id = tr.employee_id
left join payroll as pay on e.employee_id = pay.employee_id
left join shifts as sh on e.employee_id = sh.employee_id
left join overtime as ot on e.employee_id = ot.employee_id
left join locations as loc on e.location_id = loc.location_id
left join departments as d on e.department_id = d.department_id
