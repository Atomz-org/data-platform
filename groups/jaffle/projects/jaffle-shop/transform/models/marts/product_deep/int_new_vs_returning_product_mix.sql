with

orders as (

    select * from {{ ref('stg_orders') }}

),

order_items as (

    select * from {{ ref('stg_order_items') }}

),

products as (

    select * from {{ ref('stg_products') }}

),

customers as (

    select * from {{ ref('customers') }}

),

customer_first_order as (

    select
        customer_id,
        min(ordered_at) as first_order_date
    from orders
    group by 1

),

order_customer_type as (

    select
        o.order_id,
        o.customer_id,
        o.ordered_at,
        case
            when o.ordered_at = cfo.first_order_date then 'new'
            else 'returning'
        end as customer_type
    from orders as o
    inner join customer_first_order as cfo
        on o.customer_id = cfo.customer_id

),

final as (

    select
        oi.product_id,
        oct.customer_type,
        count(distinct oi.order_item_id) as item_count,
        count(distinct oct.order_id) as order_count,
        count(distinct oct.customer_id) as customer_count,
        sum(p.product_price) as total_revenue
    from order_items as oi
    inner join order_customer_type as oct
        on oi.order_id = oct.order_id
    inner join products as p
        on oi.product_id = p.product_id
    group by 1, 2

)

select * from final
