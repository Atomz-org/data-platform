with

order_items as (

    select * from {{ ref('stg_order_items') }}

),

product_pairs as (

    select
        a.product_id as product_id_a,
        b.product_id as product_id_b,
        a.order_id

    from order_items as a
    inner join order_items as b
        on a.order_id = b.order_id
        and a.product_id < b.product_id

),

pair_counts as (

    select
        product_id_a,
        product_id_b,
        count(distinct order_id) as co_occurrence_count

    from product_pairs
    group by product_id_a, product_id_b

),

product_order_counts as (

    select
        product_id,
        count(distinct order_id) as total_orders

    from order_items
    group by product_id

),

affinity as (

    select
        pc.product_id_a,
        pc.product_id_b,
        pc.co_occurrence_count,
        poc_a.total_orders as product_a_total_orders,
        poc_b.total_orders as product_b_total_orders,
        pc.co_occurrence_count * 1.0 / poc_a.total_orders as support_a,
        pc.co_occurrence_count * 1.0 / poc_b.total_orders as support_b,
        rank() over (
            partition by pc.product_id_a
            order by pc.co_occurrence_count desc
        ) as affinity_rank

    from pair_counts as pc
    inner join product_order_counts as poc_a
        on pc.product_id_a = poc_a.product_id
    inner join product_order_counts as poc_b
        on pc.product_id_b = poc_b.product_id

)

select * from affinity
