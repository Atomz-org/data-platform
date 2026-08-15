with

overtime as (

    select * from {{ ref('int_overtime_hours') }}

),

employees as (

    select
        employee_id,
        department_id
    from {{ ref('dim_employees') }}

),

departments as (

    select
        department_id,
        department_name
    from {{ ref('stg_departments') }}

),

final as (

    select
        d.department_id,
        d.department_name,
        {{ dbt.date_trunc('month', 'ot.week_start') }} as overtime_month,
        count(distinct ot.employee_id) as employees_with_overtime,
        sum(ot.total_overtime_hours) as total_overtime_hours,
        avg(ot.total_overtime_hours) as avg_overtime_hours_per_employee,
        max(ot.total_overtime_hours) as max_overtime_hours
    from overtime as ot
    inner join employees as e
        on ot.employee_id = e.employee_id
    inner join departments as d
        on e.department_id = d.department_id
    where ot.total_overtime_hours > 0
    group by 1, 2, 3

)

select * from final
