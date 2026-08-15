with

segment_usage as (

    select * from {{ ref('int_coupon_usage_by_customer_segment') }}

),

-- Total across all segments for share calculations
totals as (

    select
        sum(total_redemptions) as grand_total_redemptions,
        sum(total_net_revenue) as grand_total_net_revenue

    from segment_usage

),

-- Enrich with share metrics and incremental revenue contribution
final as (

    select
        segment_usage.customer_segment,
        segment_usage.total_redemptions,
        segment_usage.unique_customers,
        segment_usage.total_discount_given,
        segment_usage.total_order_revenue,
        segment_usage.total_net_revenue,
        segment_usage.avg_discount_per_redemption,
        segment_usage.avg_order_value,
        segment_usage.redemptions_per_customer,
        -- Share of total redemptions
        case
            when totals.grand_total_redemptions > 0
            then segment_usage.total_redemptions * 1.0 / totals.grand_total_redemptions
            else 0
        end as redemption_share,
        -- Share of total net revenue
        case
            when totals.grand_total_net_revenue > 0
            then segment_usage.total_net_revenue / totals.grand_total_net_revenue
            else 0
        end as revenue_share,
        -- Net revenue after discounts per customer
        case
            when segment_usage.unique_customers > 0
            then segment_usage.total_net_revenue / segment_usage.unique_customers
            else null
        end as net_revenue_per_customer,
        -- Discount efficiency: net revenue generated per dollar of discount
        case
            when segment_usage.total_discount_given > 0
            then segment_usage.total_net_revenue / segment_usage.total_discount_given
            else null
        end as discount_efficiency_ratio

    from segment_usage

    cross join totals

)

select * from final
