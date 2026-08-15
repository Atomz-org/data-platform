with

customer_360 as (

    select * from {{ ref('dim_customer_360') }}

),

loyalty_members as (

    select customer_id
    from {{ ref('dim_loyalty_members') }}

),

customer_classified as (

    select
        c.customer_id,
        c.customer_name,
        c.lifetime_spend,
        c.total_orders,
        c.avg_order_value,
        c.days_since_last_order,
        c.rfm_total_score,
        c.customer_tenure_days,
        case
            when lm.customer_id is not null then 'loyalty'
            else 'non_loyalty'
        end as customer_segment
    from customer_360 as c
    left join loyalty_members as lm
        on c.customer_id = lm.customer_id

),

segment_summary as (

    select
        customer_segment,
        count(distinct customer_id) as customer_count,
        round(avg(lifetime_spend), 2) as avg_lifetime_spend,
        round(avg(total_orders), 1) as avg_total_orders,
        round(avg(avg_order_value), 2) as avg_order_value,
        round(avg(days_since_last_order), 0) as avg_days_since_last_order,
        round(avg(rfm_total_score), 1) as avg_rfm_score,
        round(avg(customer_tenure_days), 0) as avg_tenure_days,
        sum(lifetime_spend) as total_segment_revenue,
        count(distinct case when total_orders > 1 then customer_id end) as repeat_customers,
        round(
            (count(distinct case when total_orders > 1 then customer_id end) * 100.0
            / nullif(count(distinct customer_id), 0)), 2
        ) as repeat_rate_pct
    from customer_classified
    group by 1

),

with_comparison as (

    select
        ss.*,
        round(
            (ss.total_segment_revenue * 100.0
            / nullif(sum(ss.total_segment_revenue) over (), 0)), 2
        ) as revenue_share_pct,
        round(
            (ss.customer_count * 100.0
            / nullif(sum(ss.customer_count) over (), 0)), 2
        ) as customer_share_pct
    from segment_summary as ss

)

select * from with_comparison
