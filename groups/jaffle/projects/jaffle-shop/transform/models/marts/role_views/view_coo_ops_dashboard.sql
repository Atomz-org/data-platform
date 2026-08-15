with

ops_scorecard as (

    select * from {{ ref('exec_ops_scorecard') }}

)

select
    reporting_month,
    avg_orders_per_labor_hour as avg_order_throughput,
    labor_cost_pct as labor_utilization_pct,
    waste_to_revenue_pct as waste_rate_pct,
    ops_health_score as overall_ops_score,
    case
        when ops_health_score >= 80 then 'excellent'
        when ops_health_score >= 60 then 'good'
        when ops_health_score >= 40 then 'needs_improvement'
        else 'critical'
    end as ops_rating

from ops_scorecard
