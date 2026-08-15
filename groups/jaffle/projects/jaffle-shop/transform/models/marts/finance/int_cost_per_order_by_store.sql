with

expense_summary as (

    select * from {{ ref('int_expense_summary_monthly') }}

),

orders as (

    select * from {{ ref('stg_orders') }}

),

monthly_expenses_by_store as (

    select
        location_id,
        expense_month,
        sum(total_expense_amount) as total_expenses,
        sum(case when is_cost_of_goods_sold then total_expense_amount else 0 end) as cogs_amount,
        sum(case when is_operating_expense then total_expense_amount else 0 end) as opex_amount

    from expense_summary
    group by 1, 2

),

monthly_orders_by_store as (

    select
        location_id,
        {{ dbt.date_trunc('month', 'ordered_at') }} as order_month,
        count(order_id) as order_count,
        sum(order_total) as total_order_revenue

    from orders
    group by 1, 2

),

cost_per_order as (

    select
        mo.location_id,
        mo.order_month as report_month,
        mo.order_count,
        mo.total_order_revenue,
        coalesce(me.total_expenses, 0) as total_expenses,
        coalesce(me.cogs_amount, 0) as cogs_amount,
        coalesce(me.opex_amount, 0) as opex_amount,
        case
            when mo.order_count > 0
                then coalesce(me.total_expenses, 0) / mo.order_count
            else null
        end as total_cost_per_order,
        case
            when mo.order_count > 0
                then coalesce(me.cogs_amount, 0) / mo.order_count
            else null
        end as cogs_per_order,
        case
            when mo.order_count > 0
                then coalesce(me.opex_amount, 0) / mo.order_count
            else null
        end as opex_per_order,
        case
            when mo.total_order_revenue > 0
                then coalesce(me.total_expenses, 0) / mo.total_order_revenue
            else null
        end as expense_to_revenue_ratio

    from monthly_orders_by_store as mo
    left join monthly_expenses_by_store as me
        on mo.location_id = me.location_id
        and mo.order_month = me.expense_month

)

select * from cost_per_order
