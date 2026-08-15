with

oi as (
    select * from {{ ref('stg_order_items') }}
),

p as (
    select * from {{ ref('stg_products') }}
),

order_items as (

    select
        oi.order_id,
        oi.product_id,
        1 as quantity,
        p.product_price as item_revenue
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

margins as (

    select
        menu_item_id as product_id,
        gross_margin
    from {{ ref('int_menu_item_margin') }}

),

with_daypart as (

    select
        o.location_id,
        case
            when o.order_hour between 6 and 10 then 'morning'
            when o.order_hour between 11 and 14 then 'lunch'
            when o.order_hour between 15 and 17 then 'afternoon'
            when o.order_hour between 18 and 21 then 'evening'
            else 'late_night'
        end as daypart,
        {{ dbt.date_trunc('month', 'o.ordered_at') }} as order_month,
        oi.item_revenue,
        coalesce(m.gross_margin, 0) as gross_margin
    from order_items as oi
    inner join orders as o on oi.order_id = o.order_id
    left join margins as m on oi.product_id = m.product_id

),

final as (

    select
        location_id,
        daypart,
        order_month,
        sum(item_revenue) as total_revenue,
        sum(gross_margin) as total_margin,
        case
            when sum(item_revenue) > 0
            then sum(gross_margin) / sum(item_revenue) * 100
            else 0
        end as gross_margin_pct,
        count(*) as item_count
    from with_daypart
    group by 1, 2, 3

)

select * from final
