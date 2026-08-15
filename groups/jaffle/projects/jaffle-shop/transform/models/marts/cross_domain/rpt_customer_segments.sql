with rfm_data as (
    select
        customer_id,
        recency_score,
        frequency_score,
        monetary_score,
        rfm_total_score,
        rfm_segment_code,
        days_since_last_order,
        order_count,
        total_spend
    from {{ ref('int_customer_rfm_scores') }}
),

segmented as (
    select
        customer_id,
        recency_score,
        frequency_score,
        monetary_score,
        rfm_total_score,
        days_since_last_order,
        order_count,
        total_spend,
        case
            when recency_score >= 4 and frequency_score >= 4 and monetary_score >= 4
                then 'Champion'
            when recency_score >= 3 and frequency_score >= 3 and monetary_score >= 3
                then 'Loyal Customer'
            when recency_score >= 4 and frequency_score <= 2
                then 'New Customer'
            when recency_score >= 3 and frequency_score >= 3 and monetary_score <= 2
                then 'Potential Loyalist'
            when recency_score >= 3 and frequency_score <= 2 and monetary_score >= 3
                then 'Big Spender'
            when recency_score <= 2 and frequency_score >= 3 and monetary_score >= 3
                then 'At Risk'
            when recency_score <= 2 and frequency_score >= 4
                then 'Cant Lose Them'
            when recency_score <= 2 and frequency_score <= 2 and monetary_score <= 2
                then 'Lost'
            when recency_score <= 2 and frequency_score >= 2
                then 'Hibernating'
            else 'Need Attention'
        end as customer_segment
    from rfm_data
)

select
    customer_segment,
    count(*) as customer_count,
    round(
        (cast(count(*) as {{ dbt.type_float() }})
        / nullif(sum(count(*)) over (), 0) * 100), 2
    ) as segment_pct,
    round(cast(avg(total_spend) as numeric), 2) as avg_spend,
    round(cast(avg(order_count) as numeric), 2) as avg_orders,
    round(cast(avg(days_since_last_order) as numeric), 0) as avg_days_since_last_order,
    round(cast(avg(rfm_total_score) as numeric), 2) as avg_rfm_score,
    sum(total_spend) as total_segment_revenue,
    round(
        (cast(sum(total_spend) as {{ dbt.type_float() }})
        / nullif(sum(sum(total_spend)) over (), 0) * 100), 2
    ) as segment_revenue_share_pct
from segmented
group by customer_segment
