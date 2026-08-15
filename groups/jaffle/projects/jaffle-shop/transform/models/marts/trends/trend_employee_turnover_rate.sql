with

monthly_headcount as (
    select
        month_start,
        sum(headcount) as headcount,
        sum(new_hires_in_month) as new_hires,
        sum(terminations_in_month) as departures
    from {{ ref('int_employee_roster_monthly') }}
    group by 1
),

trended as (
    select
        month_start,
        headcount,
        new_hires,
        departures,
        round(departures * 100.0 / nullif(headcount, 0), 2) as turnover_rate_pct,
        avg(round(departures * 100.0 / nullif(headcount, 0), 2)) over (
            order by month_start rows between 2 preceding and current row
        ) as turnover_3m_ma,
        avg(round(departures * 100.0 / nullif(headcount, 0), 2)) over (
            order by month_start rows between 11 preceding and current row
        ) as turnover_12m_ma,
        case
            when round(departures * 100.0 / nullif(headcount, 0), 2) > 15 then 'critical'
            when round(departures * 100.0 / nullif(headcount, 0), 2) > 10 then 'elevated'
            else 'normal'
        end as turnover_severity
    from monthly_headcount
)

select * from trended
