with

reviews as (

    select * from {{ ref('stg_performance_reviews') }}

),

employees as (

    select
        employee_id,
        department_id,
        location_id
    from {{ ref('stg_employees') }}

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
        {{ dbt.date_trunc('quarter', 'r.review_date') }} as review_quarter,
        count(r.review_id) as review_count,
        avg(r.overall_score) as avg_overall_score,
        avg(r.attendance_score) as avg_attendance_score,
        avg(r.quality_score) as avg_quality_score,
        avg(r.teamwork_score) as avg_teamwork_score,
        min(r.overall_score) as min_overall_score,
        max(r.overall_score) as max_overall_score,
        count(distinct r.employee_id) as employees_reviewed
    from reviews as r
    inner join employees as e
        on r.employee_id = e.employee_id
    inner join departments as d
        on e.department_id = d.department_id
    group by 1, 2, 3

)

select * from final
