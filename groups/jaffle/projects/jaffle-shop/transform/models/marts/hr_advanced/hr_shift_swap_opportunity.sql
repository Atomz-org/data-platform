with

shifts as (

    select
        shift_id,
        employee_id,
        location_id,
        shift_date,
        scheduled_start,
        scheduled_end,
        shift_type
    from {{ ref('stg_shifts') }}

),

-- Find shifts at same location on same day with different employees
potential_swaps as (

    select
        a.shift_id as shift_a,
        b.shift_id as shift_b,
        a.employee_id as employee_a,
        b.employee_id as employee_b,
        a.location_id,
        a.shift_date,
        a.shift_type as shift_a_type,
        b.shift_type as shift_b_type
    from shifts as a
    inner join shifts as b
        on a.location_id = b.location_id
        and a.shift_date = b.shift_date
        and a.employee_id != b.employee_id
        and a.shift_id < b.shift_id

),

summary as (

    select
        location_id,
        shift_date,
        count(*) as swap_opportunities,
        count(distinct employee_a) + count(distinct employee_b) as unique_employees_available
    from potential_swaps
    group by 1, 2

)

select * from summary
