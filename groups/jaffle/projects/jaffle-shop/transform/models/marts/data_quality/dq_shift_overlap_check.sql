with

shifts as (

    select * from {{ ref('stg_shifts') }}

),

-- Self-join to find overlapping shifts for the same employee on the same day
overlapping as (

    select
        s1.shift_id as shift_id_1,
        s2.shift_id as shift_id_2,
        s1.employee_id,
        s1.shift_date,
        s1.location_id as location_1,
        s2.location_id as location_2,
        s1.scheduled_start as start_1,
        s1.scheduled_end as end_1,
        s2.scheduled_start as start_2,
        s2.scheduled_end as end_2,
        s1.shift_status as status_1,
        s2.shift_status as status_2

    from shifts as s1

    inner join shifts as s2
        on s1.employee_id = s2.employee_id
        and s1.shift_date = s2.shift_date
        and s1.shift_id < s2.shift_id  -- avoid duplicate pairs and self-joins
        and s1.scheduled_start < s2.scheduled_end
        and s2.scheduled_start < s1.scheduled_end

)

select * from overlapping
