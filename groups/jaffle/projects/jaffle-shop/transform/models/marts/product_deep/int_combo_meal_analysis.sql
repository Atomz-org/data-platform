with

order_items as (

    select * from {{ ref('stg_order_items') }}

),

orders_with_multiple_items as (

    select
        order_id,
        count(order_item_id) as item_count
    from order_items
    group by 1
    having count(order_item_id) >= 3

),

product_pairs as (

    select
        a.product_id as product_a,
        b.product_id as product_b,
        count(distinct a.order_id) as co_occurrence_count
    from order_items as a
    inner join order_items as b
        on a.order_id = b.order_id
        and a.product_id < b.product_id
    inner join orders_with_multiple_items as om
        on a.order_id = om.order_id
    group by 1, 2

),

product_frequency as (

    select
        product_id,
        count(distinct order_id) as total_orders
    from order_items
    group by 1

),

final as (

    select
        pp.product_a,
        pp.product_b,
        pp.co_occurrence_count,
        pfa.total_orders as product_a_orders,
        pfb.total_orders as product_b_orders,
        case
            when pfa.total_orders > 0
                then round(cast(pp.co_occurrence_count * 100.0 / pfa.total_orders as {{ dbt.type_float() }}), 2)
            else 0
        end as pct_of_product_a_orders,
        case
            when pfb.total_orders > 0
                then round(cast(pp.co_occurrence_count * 100.0 / pfb.total_orders as {{ dbt.type_float() }}), 2)
            else 0
        end as pct_of_product_b_orders
    from product_pairs as pp
    left join product_frequency as pfa
        on pp.product_a = pfa.product_id
    left join product_frequency as pfb
        on pp.product_b = pfb.product_id

)

select * from final
