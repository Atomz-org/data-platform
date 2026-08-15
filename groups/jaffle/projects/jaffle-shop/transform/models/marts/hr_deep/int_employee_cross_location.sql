with

shifts as (

    select * from {{ ref('stg_shifts') }}

),

employees as (

    select
        employee_id,
        full_name,
        location_id as home_location_id
    from {{ ref('stg_employees') }}

),

multi_location as (

    select
        s.employee_id,
        count(distinct s.location_id) as locations_worked,
        count(s.shift_id) as total_shifts,
        min(s.shift_date) as first_shift_date,
        max(s.shift_date) as last_shift_date
    from shifts as s
    group by 1

),

final as (

    select
        ml.employee_id,
        e.full_name,
        e.home_location_id,
        ml.locations_worked,
        ml.total_shifts,
        ml.first_shift_date,
        ml.last_shift_date,
        case
            when ml.locations_worked = 1 then 'single_location'
            when ml.locations_worked = 2 then 'dual_location'
            else 'multi_location'
        end as location_flexibility
    from multi_location as ml
    inner join employees as e
        on ml.employee_id = e.employee_id

)

select * from final
