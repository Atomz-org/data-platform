with

e as (
    select * from {{ ref('dim_employees') }}
)


select
    e.department_name,
    count(*) as headcount
from e
where e.is_active = true
group by e.department_name
