with

financial_summary as (
    select * from {{ ref('exec_financial_summary_monthly') }}
)

select
    month_start,
    total_revenue,
    total_expenses,
    gross_profit,
    net_profit,
    gross_margin_pct,
    net_profit_margin_pct,
    lag(total_revenue) over (order by month_start) as prev_month_revenue,
    round(
        (total_revenue - lag(total_revenue) over (order by month_start))
        * 100.0 / nullif(lag(total_revenue) over (order by month_start), 0), 2
    ) as revenue_mom_growth_pct
from financial_summary
order by month_start desc
