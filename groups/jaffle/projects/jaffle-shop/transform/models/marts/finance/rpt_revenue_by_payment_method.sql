with

payment_mix as (

    select * from {{ ref('int_payment_method_mix') }}

),

daily_revenue as (

    select * from {{ ref('int_daily_revenue') }}

),

order_locations as (

    select
        order_id,
        location_id
    from {{ ref('stg_orders') }}

),

payment_with_location as (

    select
        pm.order_id,
        pm.payment_method,
        pm.completed_amount,
        pm.transaction_count,
        pm.first_payment_date,
        ol.location_id

    from payment_mix as pm
    left join order_locations as ol
        on pm.order_id = ol.order_id

),

method_revenue as (

    select
        pwl.payment_method,
        pwl.location_id,
        {{ dbt.date_trunc('month', 'pwl.first_payment_date') }} as revenue_month,
        count(distinct pwl.order_id) as order_count,
        sum(pwl.transaction_count) as transaction_count,
        sum(pwl.completed_amount) as payment_method_revenue

    from payment_with_location as pwl
    group by 1, 2, 3

),

with_totals as (

    select
        mr.payment_method,
        mr.location_id,
        mr.revenue_month,
        mr.order_count,
        mr.transaction_count,
        mr.payment_method_revenue,
        sum(mr.payment_method_revenue) over (
            partition by mr.location_id, mr.revenue_month
        ) as total_location_revenue,
        case
            when sum(mr.payment_method_revenue) over (
                partition by mr.location_id, mr.revenue_month
            ) > 0
            then mr.payment_method_revenue / sum(mr.payment_method_revenue) over (
                partition by mr.location_id, mr.revenue_month
            )
            else 0
        end as revenue_share_pct

    from method_revenue as mr

)

select * from with_totals
