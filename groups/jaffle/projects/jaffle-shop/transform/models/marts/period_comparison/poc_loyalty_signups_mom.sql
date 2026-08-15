with

monthly_loyalty as (
    select
        {{ sf_date_trunc('month', "enrolled_at") }} as enrollment_month,
        count(*) as signups,
        count(distinct current_tier_name) as tiers_represented
    from {{ ref('dim_loyalty_members') }}
    group by 1
),

compared as (
    select
        enrollment_month,
        signups as current_signups,
        lag(signups) over (order by enrollment_month) as prior_month_signups,
        signups - lag(signups) over (order by enrollment_month) as signups_change,
        round(((signups - lag(signups) over (order by enrollment_month))) * 100.0
            / nullif(lag(signups) over (order by enrollment_month), 0), 2) as signups_mom_pct
    from monthly_loyalty
)

select * from compared
