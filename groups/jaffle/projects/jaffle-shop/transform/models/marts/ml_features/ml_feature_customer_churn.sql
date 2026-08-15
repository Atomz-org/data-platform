with

customer_360 as (

    select * from {{ ref('dim_customer_360') }}

),

rfm as (

    select * from {{ ref('int_customer_rfm_scores') }}

),

-- Calculate order trend slope using last 6 months of orders
order_trend as (

    select
        customer_id,
        {{ dbt.date_trunc('month', 'ordered_at') }} as order_month,
        count(distinct order_id) as monthly_orders,
        row_number() over (
            partition by customer_id
            order by {{ dbt.date_trunc('month', 'ordered_at') }} desc
        ) as months_ago
    from {{ ref('orders') }}
    group by 1, 2

),

trend_calc as (

    select
        customer_id,
        -- Simple trend: compare avg of recent 3 months vs prior 3 months
        avg(case when months_ago <= 3 then monthly_orders end) as recent_3m_avg,
        avg(case when months_ago between 4 and 6 then monthly_orders end) as prior_3m_avg
    from order_trend
    where months_ago <= 6
    group by 1

),

features as (

    select
        c.customer_id,

        -- Recency features
        c.days_since_last_order,
        rfm.recency_score,

        -- Frequency features
        c.total_orders as lifetime_order_count,
        rfm.frequency_score,
        case
            when c.customer_tenure_days > 0
            then round(c.total_orders * 30.0 / c.customer_tenure_days, 2)
            else 0
        end as orders_per_month,

        -- Monetary features
        c.lifetime_spend,
        c.avg_order_value,
        rfm.monetary_score,

        -- RFM composite
        rfm.rfm_total_score,
        rfm.rfm_segment_code,

        -- Loyalty features
        c.loyalty_tier,
        case when c.loyalty_member_id is not null then 1 else 0 end as is_loyalty_member,
        coalesce(c.loyalty_points_balance, 0) as loyalty_points_balance,

        -- Engagement features
        c.distinct_stores_visited,
        coalesce(c.total_coupons_redeemed, 0) as coupons_redeemed,
        c.marketing_engagement_level,

        -- Trend features
        coalesce(tc.recent_3m_avg, 0) as recent_3m_order_avg,
        coalesce(tc.prior_3m_avg, 0) as prior_3m_order_avg,
        case
            when tc.prior_3m_avg > 0
            then round(((tc.recent_3m_avg - tc.prior_3m_avg) / tc.prior_3m_avg), 4)
            else 0
        end as order_trend_slope,

        -- Tenure
        c.customer_tenure_days,

        -- Target proxy: high churn risk if no order in 90+ days
        case
            when c.days_since_last_order > 90 then 1
            else 0
        end as churn_label_proxy

    from customer_360 as c
    inner join rfm
        on c.customer_id = rfm.customer_id
    left join trend_calc as tc
        on c.customer_id = tc.customer_id

)

select * from features
