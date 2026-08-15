with

payments as (

    select * from {{ ref('stg_payment_transactions') }}

),

orders as (

    select
        order_id,
        customer_id
    from {{ ref('stg_orders') }}

),

rfm as (

    select
        customer_id,
        rfm_segment_code as rfm_segment
    from {{ ref('int_customer_rfm_scores') }}

),

payment_with_segment as (

    select
        p.payment_method,
        r.rfm_segment,
        p.payment_amount,
        p.payment_status
    from payments as p
    inner join orders as o
        on p.order_id = o.order_id
    inner join rfm as r
        on o.customer_id = r.customer_id
    where p.payment_status = 'completed'

),

final as (

    select
        rfm_segment,
        payment_method,
        count(*) as transaction_count,
        sum(payment_amount) as total_amount,
        avg(payment_amount) as avg_amount,
        round(
            count(*) * 100.0 / sum(count(*)) over (partition by rfm_segment)
        , 2) as pct_of_segment_transactions
    from payment_with_segment
    group by 1, 2

)

select * from final
