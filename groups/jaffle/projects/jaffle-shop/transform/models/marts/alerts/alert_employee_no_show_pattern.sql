with

no_shows as (
    select
        employee_id,
        shift_date,
        location_id,
        count(*) over (
            partition by employee_id order by shift_date
            rows between 29 preceding and current row
        ) as no_shows_30d
    from {{ ref('fct_shifts') }}
    where shift_status = 'no_show'
),

alerts as (
    select
        employee_id,
        shift_date,
        location_id,
        no_shows_30d,
        'employee_no_show_pattern' as alert_type,
        case when no_shows_30d >= 5 then 'critical' else 'warning' end as severity
    from no_shows
    where no_shows_30d >= 3
)

select * from alerts
