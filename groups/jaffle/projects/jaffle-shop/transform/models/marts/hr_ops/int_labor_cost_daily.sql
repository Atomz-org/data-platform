with

labor_hours as (

    select * from {{ ref('int_labor_hours_actual') }}

),

employees as (

    select * from {{ ref('stg_employees') }}

),

positions as (

    select * from {{ ref('stg_positions') }}

),

labor_with_rates as (

    select
        labor_hours.employee_id,
        labor_hours.location_id,
        labor_hours.work_date,
        labor_hours.total_hours_worked,
        positions.min_hourly_rate as hourly_rate,
        labor_hours.total_hours_worked * positions.min_hourly_rate as estimated_labor_cost

    from labor_hours
    inner join employees
        on labor_hours.employee_id = employees.employee_id
    inner join positions
        on employees.position_id = positions.position_id

),

daily_cost as (

    select
        location_id,
        work_date,
        sum(total_hours_worked) as total_hours,
        sum(estimated_labor_cost) as total_labor_cost,
        count(distinct employee_id) as employee_count

    from labor_with_rates
    group by
        location_id,
        work_date

)

select * from daily_cost
