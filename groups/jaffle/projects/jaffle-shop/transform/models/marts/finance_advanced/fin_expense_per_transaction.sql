with

monthly_expenses as (

    select
        location_id,
        {{ dbt.date_trunc('month', 'incurred_date') }} as expense_month,
        sum(expense_amount) as total_expenses
    from {{ ref('fct_expenses') }}
    group by 1, 2

),

monthly_orders as (

    select
        location_id,
        {{ dbt.date_trunc('month', 'ordered_at') }} as order_month,
        count(order_id) as total_orders,
        sum(order_total) as total_revenue
    from {{ ref('stg_orders') }}
    group by 1, 2

),

store_names as (

    select location_id, location_name as store_name
    from {{ ref('stg_locations') }}

),

final as (

    select
        me.location_id,
        s.store_name,
        me.expense_month,
        me.total_expenses,
        coalesce(mo.total_orders, 0) as total_orders,
        coalesce(mo.total_revenue, 0) as total_revenue,
        case
            when coalesce(mo.total_orders, 0) > 0
            then me.total_expenses / mo.total_orders
            else null
        end as expense_per_transaction,
        case
            when coalesce(mo.total_revenue, 0) > 0
            then me.total_expenses / mo.total_revenue * 100
            else null
        end as expense_to_revenue_pct
    from monthly_expenses as me
    left join monthly_orders as mo
        on me.location_id = mo.location_id
        and me.expense_month = mo.order_month
    inner join store_names as s
        on me.location_id = s.location_id

)

select * from final
