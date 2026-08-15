with

campaign_orders as (

    select * from {{ ref('int_campaign_orders') }}

),

customers as (

    select * from {{ ref('customers') }}

),

orders as (

    select * from {{ ref('stg_orders') }}

),

-- Identify dormant customers: those with a gap of 90+ days between orders
customer_order_gaps as (

    select
        customer_id,
        order_id,
        ordered_at,
        lag(ordered_at) over (
            partition by customer_id
            order by ordered_at
        ) as previous_order_date,
        {{ dbt.datediff(
            'lag(ordered_at) over (partition by customer_id order by ordered_at)',
            'ordered_at',
            'day'
        ) }} as days_since_previous_order

    from orders

),

-- Orders that broke a dormancy period (90+ day gap)
reactivation_orders as (

    select
        customer_id,
        order_id,
        ordered_at as reactivation_date,
        previous_order_date,
        days_since_previous_order

    from customer_order_gaps
    where days_since_previous_order >= 90

),

-- Match reactivation orders to campaigns that may have driven them
campaign_reactivations as (

    select
        reactivation_orders.customer_id,
        reactivation_orders.order_id,
        reactivation_orders.reactivation_date,
        reactivation_orders.days_since_previous_order,
        campaign_orders.campaign_id,
        campaign_orders.campaign_name,
        campaign_orders.campaign_channel,
        campaign_orders.discount_applied,
        'campaign_coupon' as reactivation_driver

    from reactivation_orders

    inner join campaign_orders
        on reactivation_orders.order_id = campaign_orders.order_id
        and reactivation_orders.customer_id = campaign_orders.customer_id

),

-- Include customer details
final as (

    select
        campaign_reactivations.customer_id,
        customers.customer_name,
        customers.customer_type,
        customers.lifetime_spend,
        customers.count_lifetime_orders,
        campaign_reactivations.order_id,
        campaign_reactivations.reactivation_date,
        campaign_reactivations.days_since_previous_order,
        campaign_reactivations.campaign_id,
        campaign_reactivations.campaign_name,
        campaign_reactivations.campaign_channel,
        campaign_reactivations.discount_applied,
        campaign_reactivations.reactivation_driver

    from campaign_reactivations

    inner join customers
        on campaign_reactivations.customer_id = customers.customer_id

)

select * from final
