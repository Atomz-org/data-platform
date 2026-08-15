with

o as (
    select * from {{ ref('stg_orders') }}
),

r as (
    select * from {{ ref('stg_refunds') }}
),

refund_rate as (

    select
        o.customer_id,
        count(distinct o.order_id) as total_orders,
        count(distinct r.refund_id) as refund_count,
        case
            when count(distinct o.order_id) > 0
                then round(cast(count(distinct r.refund_id) * 100.0 / count(distinct o.order_id) as {{ dbt.type_float() }}), 2)
            else 0
        end as refund_rate_pct
    from o
    left join r
        on o.order_id = r.order_id
    group by 1

),

review_scores as (

    select
        customer_id,
        avg(rating) as avg_review_rating,
        count(review_id) as review_count
    from {{ ref('stg_product_reviews') }}
    group by 1

),

order_frequency as (

    select
        customer_id,
        count(order_id) as lifetime_orders,
        {{ dbt.datediff('min(ordered_at)', 'max(ordered_at)', 'day') }} as days_active
    from {{ ref('stg_orders') }}
    group by 1

),

final as (

    select
        rr.customer_id,
        rr.total_orders,
        rr.refund_rate_pct,
        coalesce(rs.avg_review_rating, 0) as avg_review_rating,
        coalesce(rs.review_count, 0) as review_count,
        of2.days_active,
        -- Composite satisfaction: low refunds + high reviews + repeat purchase
        round(cast(
            (5 - {{ sf_least(["rr.refund_rate_pct", "5"]) }}) * 20  -- refund component (0-100)
            + coalesce(rs.avg_review_rating, 3) * 20   -- review component (0-100)
            + {{ sf_least(["(of2.days_active / 30.0)", "5"]) }} * 20    -- frequency component (0-100)
        as {{ dbt.type_float() }}) / 3, 1) as satisfaction_score,
        case
            when (5 - {{ sf_least(["rr.refund_rate_pct", "5"]) }}) * 20 + coalesce(rs.avg_review_rating, 3) * 20 + {{ sf_least(["(of2.days_active / 30.0)", "5"]) }} * 20 > 200
                then 'promoter'
            when (5 - {{ sf_least(["rr.refund_rate_pct", "5"]) }}) * 20 + coalesce(rs.avg_review_rating, 3) * 20 + {{ sf_least(["(of2.days_active / 30.0)", "5"]) }} * 20 > 100
                then 'passive'
            else 'detractor'
        end as satisfaction_tier
    from refund_rate as rr
    left join review_scores as rs
        on rr.customer_id = rs.customer_id
    left join order_frequency as of2
        on rr.customer_id = of2.customer_id

)

select * from final
