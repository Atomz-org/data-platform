-- adv_org_hierarchy.sql
-- Technique: Recursive CTE (cross-database compatible)

with recursive

employees_base as (
    select * from {{ ref('dim_employees') }}
),

-- Find manager for each employee using a correlated approach via window function
employee_with_manager as (
    select
        e.employee_id,
        e.full_name,
        e.department_id,
        e.department_name,
        e.hire_date,
        mgr.employee_id as manager_id,
        mgr.full_name as manager_name
    from employees_base as e
    left join (
        select
            e2.employee_id,
            e2.full_name,
            e2.department_id,
            e2.hire_date,
            -- For each department, find the employee who is the "manager" of each other employee
            -- (the one hired earliest with a smaller employee_id)
            lead(e2.employee_id) over (partition by e2.department_id order by e2.employee_id asc) as subordinate_id
        from employees_base as e2
    ) as mgr_lookup
        on e.employee_id = mgr_lookup.subordinate_id
       and e.department_id = mgr_lookup.department_id
    left join employees_base as mgr
        on mgr_lookup.employee_id = mgr.employee_id
       and mgr.department_id = e.department_id
),

-- Simpler approach: manager is the employee with the earliest hire_date in the same department
-- who was hired before this employee
employee_manager_simple as (
    select
        e.employee_id,
        e.full_name,
        e.department_id,
        e.department_name,
        e.hire_date,
        m.employee_id as manager_id,
        m.full_name as manager_name
    from employees_base as e
    left join (
        -- For each employee, find the "manager" = earliest-hired person in same dept who was hired before them
        select
            e1.employee_id,
            e1.full_name,
            e1.department_id,
            e1.hire_date,
            e1.department_name
        from employees_base as e1
        where e1.employee_id = (
            select min(e3.employee_id)
            from employees_base as e3
            where e3.department_id = e1.department_id
              and e3.hire_date < e1.hire_date
        )
    ) as m
        on e.department_id = m.department_id
       and m.hire_date < e.hire_date
),

org_hierarchy as (
    -- Anchor: department heads (no manager)
    select
        employee_id,
        full_name,
        manager_id,
        manager_name,
        department_name,
        0 as depth_level,
        full_name as org_path
    from employee_manager_simple
    where manager_id is null

    union all

    select
        emp.employee_id,
        emp.full_name,
        emp.manager_id,
        emp.manager_name,
        emp.department_name,
        parent.depth_level + 1 as depth_level,
        parent.org_path || ' > ' || emp.full_name as org_path
    from employee_manager_simple as emp
    inner join org_hierarchy as parent
        on emp.manager_id = parent.employee_id
)

select
    employee_id,
    full_name,
    manager_id,
    manager_name,
    department_name,
    depth_level,
    org_path
from org_hierarchy
order by department_name, depth_level, employee_id
