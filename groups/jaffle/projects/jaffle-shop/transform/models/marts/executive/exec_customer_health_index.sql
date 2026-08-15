with

monthly_customers as (

    select * from {{ ref('met_monthly_customer_metrics') }}

),

churn_scores as (

    select
        count(*) as total_scored_customers,
        avg(churn_propensity_score) as avg_churn_score,
        count(case when churn_risk_tier = 'high' then 1 end) as high_risk_count,
        count(case when churn_risk_tier = 'medium' then 1 end) as medium_risk_count,
        count(case when churn_risk_tier = 'low' then 1 end) as low_risk_count,
        count(case when churn_risk_tier = 'high' then 1 end) * 100.0
            / nullif(count(*), 0) as high_risk_pct
    from {{ ref('scr_customer_churn_propensity') }}

),

-- Latest month snapshot
latest_month as (

    select * from monthly_customers
    where month_start = (select max(month_start) from monthly_customers)

),

final as (

    select
        lm.month_start as reporting_month,
        lm.total_tracked_customers,
        lm.tracked_active_customers,
        lm.dormant_customers,
        lm.churned_customers,
        lm.active_pct,
        lm.churn_pct,
        lm.new_customers,
        lm.total_orders,
        lm.total_revenue,
        lm.mom_customer_visit_change,

        -- Churn propensity summary (point-in-time)
        cs.total_scored_customers,
        cs.avg_churn_score,
        cs.high_risk_count,
        cs.medium_risk_count,
        cs.low_risk_count,
        cs.high_risk_pct,

        -- Customer health index: composite of active %, inverse churn score, growth
        round(coalesce(lm.active_pct, 0) * 0.4
            + ((100 - coalesce(cs.avg_churn_score, 50)) * 0.4)
            + (case
                when coalesce(lm.mom_customer_visit_change, 0) > 0 then 20
                when coalesce(lm.mom_customer_visit_change, 0) = 0 then 10
                else 0
            end), 1) as customer_health_index

    from latest_month as lm

    cross join churn_scores as cs

)

select * from final
