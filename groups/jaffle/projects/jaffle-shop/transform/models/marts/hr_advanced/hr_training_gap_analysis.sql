with

tc as (
    select * from {{ ref('stg_training_courses') }}
),

required_training as (

    select
        tc.training_course_id,
        tc.course_name,
        tc.course_category as required_for_department,
        tc.is_required
    from tc
    where tc.is_required = true

),

completed as (

    select
        employee_id,
        training_course_id,
        completed_date
    from {{ ref('stg_training_completions') }}

),

employees as (

    select
        employee_id,
        full_name,
        position_title,
        department_name
    from {{ ref('dim_employees') }}
    where is_active = true

),

gaps as (

    select
        e.employee_id,
        e.full_name,
        e.position_title,
        e.department_name,
        rt.training_course_id,
        rt.course_name,
        case when c.employee_id is not null then true else false end as is_completed,
        c.completed_date
    from employees as e
    cross join required_training as rt
    left join completed as c
        on e.employee_id = c.employee_id
        and rt.training_course_id = c.training_course_id
    where rt.required_for_department = e.department_name
        or rt.required_for_department is null

),

final as (

    select
        employee_id,
        full_name,
        position_title,
        department_name,
        count(*) as required_courses,
        sum(case when is_completed then 1 else 0 end) as completed_courses,
        sum(case when not is_completed then 1 else 0 end) as missing_courses,
        case
            when count(*) > 0
            then cast(sum(case when is_completed then 1 else 0 end) as {{ dbt.type_float() }})
                / count(*) * 100
            else 0
        end as training_completion_pct
    from gaps
    group by 1, 2, 3, 4

)

select * from final
