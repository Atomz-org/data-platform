with

daily_shifts as (
    select
        shift_date,
        location_id,
        count(*) as shift_count,
        sum(scheduled_hours) as total_hours,
        avg(scheduled_hours) as avg_shift_length
    from {{ ref('fct_shifts') }}
    group by 1, 2
),

trended as (
    select
        shift_date,
        location_id,
        shift_count,
        total_hours,
        avg_shift_length,
        avg(total_hours) over (
            partition by location_id order by shift_date
            rows between 6 preceding and current row
        ) as hours_7d_ma,
        avg(total_hours) over (
            partition by location_id order by shift_date
            rows between 27 preceding and current row
        ) as hours_28d_ma,
        avg(avg_shift_length) over (
            partition by location_id order by shift_date
            rows between 6 preceding and current row
        ) as avg_length_7d_ma
    from daily_shifts
)

select * from trended
