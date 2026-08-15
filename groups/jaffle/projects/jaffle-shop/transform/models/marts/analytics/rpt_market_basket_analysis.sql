with

order_items as (

    select * from {{ ref('stg_order_items') }}

),

products as (

    select
        product_id,
        product_name,
        product_type
    from {{ ref('stg_products') }}

),

order_stats as (

    select
        order_id,
        count(order_item_id) as items_in_basket,
        count(distinct product_id) as distinct_products,
        count(order_item_id) as basket_item_count
    from order_items
    group by 1

),

basket_summary as (

    select
        avg(items_in_basket) as avg_items_per_basket,
        avg(basket_item_count) as avg_basket_item_count,
        count(*) as total_baskets,
        count(case when items_in_basket = 1 then 1 end) as single_item_baskets,
        count(case when items_in_basket = 2 then 1 end) as two_item_baskets,
        count(case when items_in_basket >= 3 then 1 end) as multi_item_baskets
    from order_stats

),

top_pairs as (

    select
        a.product_id as product_a_id,
        b.product_id as product_b_id,
        count(distinct a.order_id) as pair_frequency
    from order_items as a
    inner join order_items as b
        on a.order_id = b.order_id
        and a.product_id < b.product_id
    group by 1, 2

),

top_pairs_ranked as (

    select
        tp.product_a_id,
        pa.product_name as product_a_name,
        tp.product_b_id,
        pb.product_name as product_b_name,
        tp.pair_frequency,
        row_number() over (order by tp.pair_frequency desc) as pair_rank
    from top_pairs as tp
    left join products as pa on tp.product_a_id = pa.product_id
    left join products as pb on tp.product_b_id = pb.product_id

)

select * from top_pairs_ranked
where pair_rank <= 50
