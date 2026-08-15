with

customer_360 as (

    select * from {{ ref('dim_customer_360') }}

),

churn_risk as (

    select
        customer_id,
        churn_propensity_score,
        churn_risk_tier
    from {{ ref('scr_customer_churn_propensity') }}

),

monthly_metrics as (

    select
        month_start,
        tracked_active_customers,
        total_tracked_customers
    from {{ ref('met_monthly_customer_metrics') }}

),

latest_monthly as (

    select
        month_start,
        tracked_active_customers,
        total_tracked_customers,
        row_number() over (order by month_start desc) as rn
    from monthly_metrics

),

customer_health as (

    select
        c.customer_id,
        c.customer_name,
        c.total_orders,
        c.lifetime_spend,
        c.rfm_segment_code as rfm_segment,
        c.rfm_total_score,
        c.loyalty_tier,
        c.days_since_last_order,
        cr.churn_propensity_score,
        cr.churn_risk_tier
    from customer_360 as c
    left join churn_risk as cr
        on c.customer_id = cr.customer_id

),

summary as (

    select
        count(distinct customer_id) as total_customers,
        count(case when churn_risk_tier = 'high' then 1 end) as high_risk_customers,
        count(case when churn_risk_tier = 'medium' then 1 end) as medium_risk_customers,
        count(case when churn_risk_tier = 'low' then 1 end) as low_risk_customers,
        avg(lifetime_spend) as avg_lifetime_spend,
        avg(total_orders) as avg_orders_per_customer,
        avg(churn_propensity_score) as avg_churn_propensity_score
    from customer_health

)

select * from summary
