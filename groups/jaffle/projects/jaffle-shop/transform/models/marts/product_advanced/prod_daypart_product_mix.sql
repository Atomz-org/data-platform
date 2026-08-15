with

oi as (
    select * from {{ ref('stg_order_items') }}
),

p as (
    select * from {{ ref('stg_products') }}
),

order_items as (

    select oi.order_id, oi.product_id, 1 as quantity, p.product_price
    from oi
    inner join p on oi.product_id = p.product_id

),

orders as (

    select
        order_id,
        location_id,
        ordered_at,
        extract(hour from ordered_at) as order_hour
    from {{ ref('stg_orders') }}

),

products as (

    select product_id, product_name, product_type
    from {{ ref('stg_products') }}

),

with_daypart as (

    select
        p.product_id,
        p.product_name,
        p.product_type,
        case
            when o.order_hour between 6 and 10 then 'morning'
            when o.order_hour between 11 and 14 then 'lunch'
            when o.order_hour between 15 and 17 then 'afternoon'
            when o.order_hour between 18 and 21 then 'evening'
            else 'late_night'
        end as daypart,
        sum(oi.quantity) as total_quantity,
        sum(oi.product_price * oi.quantity) as total_revenue
    from order_items as oi
    inner join orders as o on oi.order_id = o.order_id
    inner join products as p on oi.product_id = p.product_id
    group by 1, 2, 3, 4

),

final as (

    select
        product_id,
        product_name,
        product_type,
        daypart,
        total_quantity,
        total_revenue,
        rank() over (partition by daypart order by total_quantity desc) as daypart_rank,
        cast(total_quantity as {{ dbt.type_float() }})
            / nullif(sum(total_quantity) over (partition by daypart), 0) * 100 as daypart_share_pct
    from with_daypart

)

select * from final
