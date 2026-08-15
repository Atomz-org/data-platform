with

monthly_spend as (

    select * from {{ ref('int_supplier_spend_monthly') }}

),

with_trends as (

    select
        supplier_id,
        supplier_name,
        order_month,
        count_purchase_orders,
        total_spend,
        avg_unit_cost,
        total_quantity_ordered,
        lag(total_spend) over (
            partition by supplier_id
            order by order_month
        ) as prev_month_spend,
        lag(total_spend, 12) over (
            partition by supplier_id
            order by order_month
        ) as same_month_last_year_spend,
        case
            when lag(total_spend) over (
                partition by supplier_id
                order by order_month
            ) > 0
                then (total_spend - lag(total_spend) over (
                    partition by supplier_id
                    order by order_month
                )) * 1.0 / lag(total_spend) over (
                    partition by supplier_id
                    order by order_month
                )
            else null
        end as mom_spend_change,
        case
            when lag(total_spend, 12) over (
                partition by supplier_id
                order by order_month
            ) > 0
                then (total_spend - lag(total_spend, 12) over (
                    partition by supplier_id
                    order by order_month
                )) * 1.0 / lag(total_spend, 12) over (
                    partition by supplier_id
                    order by order_month
                )
            else null
        end as yoy_spend_change,
        sum(total_spend) over (
            partition by supplier_id
            order by order_month
        ) as cumulative_spend

    from monthly_spend

)

select * from with_trends
