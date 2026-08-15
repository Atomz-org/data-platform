with

employees as (

    select
        employee_id,
        full_name,
        department_name,
        position_title,
        location_id
    from {{ ref('dim_employees') }}
    where is_active = true

),

training_completed as (

    select
        employee_id,
        training_course_id,
        completed_date
    from {{ ref('stg_training_completions') }}

),

courses as (

    select
        training_course_id,
        course_name,
        course_category as course_department
    from {{ ref('stg_training_courses') }}

),

cross_dept_training as (

    select
        e.employee_id,
        e.full_name,
        e.department_name as home_department,
        e.position_title,
        count(distinct c.course_department) as departments_trained_in,
        count(distinct tc.training_course_id) as total_courses_completed,
        count(distinct case when c.course_department != e.department_name then tc.training_course_id end) as cross_dept_courses
    from employees as e
    left join training_completed as tc on e.employee_id = tc.employee_id
    left join courses as c on tc.training_course_id = c.training_course_id
    group by 1, 2, 3, 4

),

final as (

    select
        employee_id,
        full_name,
        home_department,
        position_title,
        departments_trained_in,
        total_courses_completed,
        cross_dept_courses,
        case
            when departments_trained_in >= 3 then 'highly_versatile'
            when departments_trained_in = 2 then 'moderately_versatile'
            else 'specialist'
        end as versatility_level
    from cross_dept_training

)

select * from final
