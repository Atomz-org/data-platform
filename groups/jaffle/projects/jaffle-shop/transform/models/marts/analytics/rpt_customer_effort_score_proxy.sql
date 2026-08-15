with

refunds as (

    select
        order_id,
        refund_amount,
        refund_reason
    from {{ ref('stg_refunds') }}

),

orders as (

    select
        order_id,
        customer_id,
        location_id,
        order_total,
        ordered_at
    from {{ ref('stg_orders') }}

),

monthly_effort as (

    select
        {{ dbt.date_trunc('month', 'o.ordered_at') }} as effort_month,
        o.location_id,
        count(distinct o.order_id) as total_orders,
        count(distinct r.order_id) as orders_with_refund,
        sum(coalesce(r.refund_amount, 0)) as total_refund_amount,
        case
            when count(distinct o.order_id) > 0
                then round(cast(
                    count(distinct r.order_id) * 100.0 / count(distinct o.order_id)
                as {{ dbt.type_float() }}), 2)
            else 0
        end as refund_rate_pct
    from orders as o
    left join refunds as r
        on o.order_id = r.order_id
    group by 1, 2

),

final as (

    select
        effort_month,
        location_id,
        total_orders,
        orders_with_refund,
        total_refund_amount,
        refund_rate_pct,
        case
            when refund_rate_pct < 2 then 'low_effort'
            when refund_rate_pct < 5 then 'moderate_effort'
            else 'high_effort'
        end as effort_tier
    from monthly_effort

)

select * from final
