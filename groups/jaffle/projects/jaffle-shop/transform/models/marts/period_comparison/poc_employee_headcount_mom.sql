with

monthly_headcount as (
    select
        month_start,
        sum(headcount) as headcount,
        sum(new_hires_in_month) as new_hires
    from {{ ref('int_employee_roster_monthly') }}
    group by 1
),

compared as (
    select
        month_start,
        headcount as current_headcount,
        lag(headcount) over (order by month_start) as prior_month_headcount,
        new_hires as current_new_hires,
        lag(new_hires) over (order by month_start) as prior_month_new_hires,
        headcount - lag(headcount) over (order by month_start) as headcount_change,
        round(((headcount - lag(headcount) over (order by month_start))) * 100.0
            / nullif(lag(headcount) over (order by month_start), 0), 2) as headcount_mom_pct
    from monthly_headcount
)

select * from compared
