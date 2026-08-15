-- adv_first_purchase_product.sql
-- Technique: Correlated Subquery
-- Finds the product from each customer's earliest order using a correlated subquery.
-- The subquery correlates on customer_id to find the minimum order date, then
-- joins back to get the actual product details.

with orders as (

    select * from {{ ref('stg_orders') }}

),

order_items as (

    select * from {{ ref('stg_order_items') }}

),

products as (

    select * from {{ ref('stg_products') }}

),

customers as (

    select * from {{ ref('stg_customers') }}

),

-- For each customer, find the product(s) from their very first order
-- using a correlated subquery to identify the earliest order
first_purchase as (

    select
        c.customer_id,
        c.customer_name,
        o.order_id as first_order_id,
        o.ordered_at as first_order_date,
        o.order_total as first_order_total,
        oi.product_id,
        p.product_name,
        p.product_type,
        p.product_price

    from customers as c

    -- Join to orders, filtering to only the first order via correlated subquery
    inner join orders as o
        on c.customer_id = o.customer_id
        and o.ordered_at = (
            -- Correlated subquery: find earliest order date for this customer
            select min(o2.ordered_at)
            from orders as o2
            where o2.customer_id = c.customer_id
        )

    inner join order_items as oi
        on o.order_id = oi.order_id

    inner join products as p
        on oi.product_id = p.product_id

)

select
    customer_id,
    customer_name,
    first_order_id,
    first_order_date,
    first_order_total,
    product_id,
    product_name,
    product_type,
    product_price
from first_purchase
order by customer_id, product_id
