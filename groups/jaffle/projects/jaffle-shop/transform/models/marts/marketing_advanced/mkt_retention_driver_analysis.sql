with

customers as (

    select
        customer_id,
        rfm_segment_code as rfm_segment,
        total_orders,
        days_since_last_order,
        lifetime_spend,
        avg_order_value
    from {{ ref('dim_customer_360') }}

),

rfm as (

    select
        customer_id,
        recency_score,
        frequency_score,
        monetary_score
    from {{ ref('int_customer_rfm_scores') }}

),

loyalty as (

    select
        customer_id,
        current_tier_name,
        enrolled_at
    from {{ ref('dim_loyalty_members') }}

),

final as (

    select
        c.customer_id,
        c.rfm_segment,
        c.total_orders,
        c.days_since_last_order,
        c.lifetime_spend,
        c.avg_order_value,
        r.recency_score,
        r.frequency_score,
        r.monetary_score,
        case when l.customer_id is not null then true else false end as is_loyalty_member,
        l.current_tier_name as loyalty_tier,
        case
            when c.days_since_last_order <= 60 then 'retained'
            else 'lapsed'
        end as retention_status,
        -- Retention driver flags
        case when l.customer_id is not null then 1 else 0 end as loyalty_factor,
        case when c.total_orders > 5 then 1 else 0 end as high_frequency_factor,
        case when c.avg_order_value > 30 then 1 else 0 end as high_value_factor,
        case when r.recency_score >= 4 then 1 else 0 end as recent_engagement_factor
    from customers as c
    left join rfm as r on c.customer_id = r.customer_id
    left join loyalty as l on c.customer_id = l.customer_id

)

select * from final
