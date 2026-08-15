with

purchase_orders as (

    select * from {{ ref('fct_purchase_orders') }}

),

monthly_summary as (

    select
        {{ dbt.date_trunc('month', 'ordered_at') }} as order_month,
        count(purchase_order_id) as total_orders,
        sum(total_amount) as total_value,
        avg(total_amount) as avg_order_value,
        sum(total_quantity_ordered) as total_quantity,
        avg(total_quantity_ordered) as avg_quantity_per_order,
        avg(count_line_items) as avg_line_items_per_order,
        sum(case when is_cancelled then 1 else 0 end) as cancelled_orders,
        sum(case when is_completed then 1 else 0 end) as completed_orders,
        case
            when count(purchase_order_id) > 0
                then sum(case when is_cancelled then 1 else 0 end) * 1.0
                    / count(purchase_order_id)
            else 0
        end as cancellation_rate

    from purchase_orders

    group by {{ dbt.date_trunc('month', 'ordered_at') }}

),

with_trends as (

    select
        *,
        lag(total_orders) over (order by order_month) as prev_month_orders,
        lag(total_value) over (order by order_month) as prev_month_value,
        case
            when lag(total_orders) over (order by order_month) > 0
                then (total_orders - lag(total_orders) over (order by order_month)) * 1.0
                    / lag(total_orders) over (order by order_month)
            else null
        end as order_count_mom_change,
        case
            when lag(total_value) over (order by order_month) > 0
                then (total_value - lag(total_value) over (order by order_month)) * 1.0
                    / lag(total_value) over (order by order_month)
            else null
        end as order_value_mom_change

    from monthly_summary

)

select * from with_trends
