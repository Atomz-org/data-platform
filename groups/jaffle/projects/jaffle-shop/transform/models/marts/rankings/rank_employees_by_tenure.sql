with

t as (
    select * from {{ ref('int_employee_tenure') }}
),

e as (
    select * from {{ ref('stg_employees') }}
),

employee_tenure as (
    select
        t.employee_id,
        e.full_name,
        t.tenure_days,
        e.department_id,
        case when e.employment_status = 'active' then true else false end as is_active
    from t
    inner join e on t.employee_id = e.employee_id
),

ranked as (
    select
        employee_id,
        full_name,
        tenure_days,
        department_id,
        is_active,
        rank() over (order by tenure_days desc) as tenure_rank,
        rank() over (partition by department_id order by tenure_days desc) as dept_tenure_rank,
        ntile(4) over (order by tenure_days desc) as tenure_quartile
    from employee_tenure
)

select * from ranked
