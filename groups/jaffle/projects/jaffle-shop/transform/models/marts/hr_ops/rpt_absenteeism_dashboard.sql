with

absenteeism as (

    select * from {{ ref('int_absenteeism_rate') }}

),

employees as (

    select * from {{ ref('dim_employees') }}

),

locations as (

    select * from {{ ref('stg_locations') }}

),

absenteeism_enriched as (

    select
        absenteeism.employee_id,
        absenteeism.location_id,
        locations.location_name,
        employees.department_name,
        employees.position_title,
        employees.is_active,
        absenteeism.total_scheduled_shifts,
        absenteeism.absent_shifts,
        absenteeism.attended_shifts,
        absenteeism.absenteeism_rate_pct

    from absenteeism
    inner join employees
        on absenteeism.employee_id = employees.employee_id
    left join locations
        on absenteeism.location_id = locations.location_id

),

by_store as (

    select
        location_id,
        location_name,
        count(distinct employee_id) as employee_count,
        sum(total_scheduled_shifts) as total_shifts,
        sum(absent_shifts) as total_absences,
        round(avg(absenteeism_rate_pct), 1) as avg_absenteeism_rate_pct,
        sum(case when absenteeism_rate_pct > 10 then 1 else 0 end) as high_absenteeism_employees

    from absenteeism_enriched
    group by
        location_id,
        location_name

),

by_department as (

    select
        department_name,
        count(distinct employee_id) as employee_count,
        sum(total_scheduled_shifts) as total_shifts,
        sum(absent_shifts) as total_absences,
        round(avg(absenteeism_rate_pct), 1) as avg_absenteeism_rate_pct,
        sum(case when absenteeism_rate_pct > 10 then 1 else 0 end) as high_absenteeism_employees

    from absenteeism_enriched
    group by department_name

),

combined as (

    select
        'store' as dimension,
        location_name as dimension_value,
        employee_count,
        total_shifts,
        total_absences,
        avg_absenteeism_rate_pct,
        high_absenteeism_employees

    from by_store

    union all

    select
        'department' as dimension,
        department_name as dimension_value,
        employee_count,
        total_shifts,
        total_absences,
        avg_absenteeism_rate_pct,
        high_absenteeism_employees

    from by_department

)

select * from combined
