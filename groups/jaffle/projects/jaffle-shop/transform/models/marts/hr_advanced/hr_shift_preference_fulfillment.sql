with

shifts as (
    select
        shift_id,
        employee_id,
        shift_date,
        shift_type,
        location_id,
        shift_status
    from {{ ref('fct_shifts') }}
),

popular_shifts as (
    select
        location_id,
        shift_type as popular_shift_type,
        shift_count
    from {{ ref('int_shift_preference_pattern') }}
    where popularity_rank = 1
),

matched as (
    select
        s.employee_id,
        s.shift_date,
        s.shift_type as assigned_shift,
        ps.popular_shift_type,
        case
            when s.shift_type = ps.popular_shift_type then true
            else false
        end as preference_met
    from shifts as s
    left join popular_shifts as ps on s.location_id = ps.location_id
    where s.shift_status != 'cancelled'
),

employee_summary as (
    select
        employee_id,
        count(*) as total_shifts,
        count(case when preference_met then 1 end) as matched_shifts,
        round(count(case when preference_met then 1 end) * 100.0 / nullif(count(*), 0), 2) as fulfillment_pct
    from matched
    group by 1
)

select * from employee_summary
