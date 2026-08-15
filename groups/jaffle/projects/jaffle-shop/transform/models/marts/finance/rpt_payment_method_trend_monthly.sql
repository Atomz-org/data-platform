with

payment_mix as (

    select * from {{ ref('int_payment_method_mix') }}

),

orders as (

    select
        order_id,
        location_id,
        ordered_at

    from {{ ref('stg_orders') }}

),

monthly_method as (

    select
        {{ dbt.date_trunc('month', 'o.ordered_at') }} as report_month,
        o.location_id,
        pm.payment_method,
        count(distinct pm.order_id) as order_count,
        sum(pm.transaction_count) as transaction_count,
        sum(pm.method_total) as method_total,
        sum(pm.completed_amount) as completed_amount,
        sum(pm.failed_amount) as failed_amount

    from payment_mix as pm
    inner join orders as o
        on pm.order_id = o.order_id
    group by 1, 2, 3

),

with_share as (

    select
        report_month,
        location_id,
        payment_method,
        order_count,
        transaction_count,
        method_total,
        completed_amount,
        failed_amount,
        sum(method_total) over (
            partition by report_month, location_id
        ) as location_month_total,
        case
            when sum(method_total) over (
                partition by report_month, location_id
            ) > 0
                then method_total / sum(method_total) over (
                    partition by report_month, location_id
                )
            else 0
        end as revenue_share_pct,
        lag(method_total) over (
            partition by location_id, payment_method
            order by report_month
        ) as prev_month_total,
        case
            when lag(method_total) over (
                partition by location_id, payment_method
                order by report_month
            ) > 0
                then (method_total - lag(method_total) over (
                    partition by location_id, payment_method
                    order by report_month
                )) / lag(method_total) over (
                    partition by location_id, payment_method
                    order by report_month
                )
            else null
        end as mom_growth_rate

    from monthly_method

)

select * from with_share
