with first_orders as (
    select
        customer_id,
        min_by(order_id, ordered_at) as first_order_id,
        cast(min_by(order_total, ordered_at) as float) as first_order_total,
        min(ordered_at) as first_order_date
    from {{ ref('stg_orders') }}
    group by customer_id
),

first_purchase_attributed as (
    select
        fo.customer_id,
        fo.first_order_id,
        fo.first_order_total,
        fo.first_order_date,
        acq.acquisition_source,
        acq.campaign_name,
        acq.campaign_channel,
        acq.referrer_customer_id,
        acq.acquired_at
    from first_orders fo
    inner join {{ ref('int_customer_acquisition_source') }} acq
        on fo.customer_id = acq.customer_id
),

channel_summary as (
    select
        coalesce(fpa.campaign_channel, fpa.acquisition_source) as attribution_channel,
        fpa.acquisition_source,
        count(distinct fpa.customer_id) as customers,
        sum(fpa.first_order_total) as total_first_order_revenue,
        avg(fpa.first_order_total) as avg_first_order_value,
        min(fpa.first_order_date) as earliest_first_purchase,
        max(fpa.first_order_date) as latest_first_purchase
    from first_purchase_attributed fpa
    group by 1, 2
),

grand_total as (
    select count(distinct customer_id) as total_customers
    from {{ ref('int_customer_acquisition_source') }}
)

select
    cs.attribution_channel,
    cs.acquisition_source,
    cs.customers,
    cs.total_first_order_revenue,
    cs.avg_first_order_value,
    cs.earliest_first_purchase,
    cs.latest_first_purchase,
    case
        when gt.total_customers > 0
        then cs.customers * 1.0 / gt.total_customers
        else 0
    end as customer_share

from channel_summary cs
cross join grand_total gt
order by cs.customers desc
