with

oi as (
    select * from {{ ref('order_items') }}
),

p as (
    select * from {{ ref('stg_products') }}
),

loy as (
    select * from {{ ref('dim_loyalty_members') }}
),

orders as (

    select * from {{ ref('orders') }}

),

order_items as (

    select * from {{ ref('order_items') }}

),

customers as (

    select * from {{ ref('customers') }}

),

locations as (

    select * from {{ ref('stg_locations') }}

),

products as (

    select * from {{ ref('stg_products') }}

),

rfm as (

    select * from {{ ref('int_customer_rfm_scores') }}

),

ltv as (

    select * from {{ ref('int_customer_ltv') }}

),

loyalty as (

    select * from {{ ref('dim_loyalty_members') }}

),

order_item_counts as (

    select
        order_id,
        count(*) as item_count,
        sum(case when p.is_food_item then 1 else 0 end) as food_item_count,
        sum(case when p.is_drink_item then 1 else 0 end) as drink_item_count,
        count(distinct oi.product_id) as distinct_product_count,
        sum(oi.supply_cost) as total_supply_cost,
        sum(p.product_price) as items_subtotal

    from oi
    left join p
        on oi.product_id = p.product_id
    group by order_id

),

customer_order_seq as (

    select
        order_id,
        customer_id,
        ordered_at,
        row_number() over (
            partition by customer_id order by ordered_at
        ) as customer_order_number,
        lag(ordered_at) over (
            partition by customer_id order by ordered_at
        ) as previous_order_at

    from {{ ref('orders') }}

),

coupon_usage as (

    select
        order_id,
        count(*) as coupon_count,
        sum(discount_applied) as coupon_discount_applied

    from {{ ref('fct_coupon_redemptions') }}
    group by order_id

)

select
    -- Order fields
    o.order_id,
    o.customer_id,
    o.location_id,
    o.ordered_at,
    o.subtotal,
    o.tax_paid,
    o.order_total,
    o.order_cost,
    o.order_items_subtotal,
    o.count_order_items,
    o.count_food_items,
    o.count_drink_items,
    o.is_food_order,
    o.is_drink_order,
    o.customer_order_number,

    -- Order-level computed fields
    oic.item_count,
    oic.food_item_count,
    oic.drink_item_count,
    oic.distinct_product_count,
    oic.total_supply_cost,
    oic.items_subtotal,
    oic.food_item_count > 0 as has_food,
    oic.drink_item_count > 0 as has_drink,
    oic.food_item_count > 0 and oic.drink_item_count > 0 as is_mixed_order,

    -- Customer fields
    c.customer_name,
    c.customer_type,
    c.first_ordered_at as customer_first_ordered_at,
    c.last_ordered_at as customer_last_ordered_at,
    c.lifetime_spend as customer_lifetime_spend,
    c.count_lifetime_orders as customer_lifetime_orders,
    c.lifetime_spend_pretax as customer_lifetime_spend_pretax,
    c.lifetime_tax_paid as customer_lifetime_tax_paid,

    -- Location fields
    l.location_name as store_name,
    l.tax_rate as store_tax_rate,
    l.opened_date as store_opened_date,

    -- Time dimensions
    extract(year from o.ordered_at) as order_year,
    extract(month from o.ordered_at) as order_month,
    extract(quarter from o.ordered_at) as order_quarter,
    {{ day_of_week_number('o.ordered_at') }} as order_day_of_week,
    case {{ day_of_week_number('o.ordered_at') }}
        when 0 then 'Sunday'
        when 1 then 'Monday'
        when 2 then 'Tuesday'
        when 3 then 'Wednesday'
        when 4 then 'Thursday'
        when 5 then 'Friday'
        when 6 then 'Saturday'
    end as order_day_name,
    extract(hour from o.ordered_at) as order_hour,
    {{ day_of_week_number('o.ordered_at') }} in (0, 6) as is_weekend,
    extract(month from o.ordered_at) = 12
        and extract(day from o.ordered_at) >= 20 as is_holiday_proxy,

    -- Customer RFM context
    rfm.recency_score as customer_recency_score,
    rfm.frequency_score as customer_frequency_score,
    rfm.monetary_score as customer_monetary_score,
    rfm.rfm_total_score as customer_rfm_total_score,
    rfm.rfm_segment_code as customer_rfm_segment,

    -- Customer LTV context
    ltv.ltv_tier as customer_ltv_bucket,
    ltv.avg_order_value as customer_avg_order_value,
    ltv.distinct_products_purchased as customer_distinct_products,
    ltv.customer_tenure_days,

    -- Loyalty context
    loy.loyalty_member_id is not null as is_loyalty_member,
    loy.current_tier_name as loyalty_tier,
    loy.current_points_balance as loyalty_points_balance,
    loy.enrolled_at as loyalty_enrolled_at,
    loy.is_active_member as is_loyalty_active,

    -- Customer order sequence context
    cos.customer_order_number as customer_order_seq_number,
    cos.previous_order_at,
    {{ dbt.datediff("cos.previous_order_at", "o.ordered_at", "day") }} as days_since_previous_order,

    -- Coupon context
    cu.coupon_count is not null and cu.coupon_count > 0 as has_coupon,
    coalesce(cu.coupon_count, 0) as coupon_count,
    coalesce(cu.coupon_discount_applied, 0) as coupon_discount_applied,

    -- Profitability
    o.order_total - coalesce(oic.total_supply_cost, 0) as gross_profit,
    case
        when o.order_total > 0
        then (o.order_total - coalesce(oic.total_supply_cost, 0)) * 100.0 / o.order_total
        else 0
    end as gross_margin_pct

from orders as o
left join order_item_counts as oic on o.order_id = oic.order_id
left join customers as c on o.customer_id = c.customer_id
left join locations as l on o.location_id = l.location_id
left join rfm on o.customer_id = rfm.customer_id
left join ltv on o.customer_id = ltv.customer_id
left join loy on o.customer_id = loy.customer_id
left join customer_order_seq as cos on o.order_id = cos.order_id
left join coupon_usage as cu on o.order_id = cu.order_id
