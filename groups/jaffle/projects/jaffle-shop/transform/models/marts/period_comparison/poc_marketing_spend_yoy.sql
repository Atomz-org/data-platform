with

monthly_marketing as (
    select month_start, total_marketing_spend from {{ ref('met_monthly_marketing_metrics') }}
),

compared as (
    select
        month_start,
        total_marketing_spend as current_spend,
        lag(total_marketing_spend, 12) over (order by month_start) as prior_year_spend,
        round((total_marketing_spend - lag(total_marketing_spend, 12) over (order by month_start)) * 100.0
            / nullif(lag(total_marketing_spend, 12) over (order by month_start), 0), 2) as spend_yoy_pct
    from monthly_marketing
)

select * from compared
