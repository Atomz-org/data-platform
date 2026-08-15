with monthly as (
    select
        month_start,
        headcount,
        terminations_in_month as departures
    from {{ ref('int_employee_roster_monthly') }}
),
agg as (
    select
        month_start,
        sum(headcount) as headcount,
        sum(departures) as departures
    from monthly
    group by 1
),
final as (
    select
        month_start,
        headcount,
        departures,
        round(departures * 100.0 / nullif(headcount, 0), 2) as turnover_rate_pct,
        round(departures * 12.0 / nullif(headcount, 0) * 100, 2) as annualized_turnover_pct
    from agg
)
select * from final
