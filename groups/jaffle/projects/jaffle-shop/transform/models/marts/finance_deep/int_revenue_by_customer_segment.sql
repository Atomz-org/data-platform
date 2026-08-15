with

rfm as (

    select * from {{ ref('int_customer_rfm_scores') }}

),

orders as (

    select * from {{ ref('stg_orders') }}

),

order_revenue as (

    select
        o.customer_id,
        {{ dbt.date_trunc('month', 'o.ordered_at') }} as revenue_month,
        sum(o.order_total) as total_revenue,
        count(o.order_id) as order_count
    from orders as o
    group by 1, 2

),

final as (

    select
        r.rfm_segment_code as rfm_segment,
        orv.revenue_month,
        count(distinct orv.customer_id) as customer_count,
        sum(orv.total_revenue) as segment_revenue,
        sum(orv.order_count) as segment_orders,
        avg(orv.total_revenue) as avg_revenue_per_customer
    from order_revenue as orv
    inner join rfm as r
        on orv.customer_id = r.customer_id
    group by 1, 2

)

select * from final
