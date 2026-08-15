with

expenses as (

    select
        location_id,
        {{ dbt.date_trunc('month', 'incurred_date') }} as expense_month,
        sum(expense_amount) as monthly_expenses
    from {{ ref('stg_expenses') }}
    group by 1, 2

),

orders as (

    select
        location_id,
        {{ dbt.date_trunc('month', 'ordered_at') }} as order_month,
        count(order_id) as monthly_orders,
        sum(order_total) as monthly_revenue
    from {{ ref('stg_orders') }}
    group by 1, 2

),

final as (

    select
        o.location_id,
        o.order_month,
        o.monthly_orders,
        o.monthly_revenue,
        coalesce(e.monthly_expenses, 0) as monthly_expenses,
        case
            when o.monthly_orders > 0
                then round(cast(coalesce(e.monthly_expenses, 0) as {{ dbt.type_float() }}) / o.monthly_orders, 2)
            else null
        end as cost_per_order,
        case
            when o.monthly_revenue > 0
                then round(cast(coalesce(e.monthly_expenses, 0) as {{ dbt.type_float() }}) * 100.0 / o.monthly_revenue, 2)
            else null
        end as expense_revenue_ratio_pct
    from orders as o
    left join expenses as e
        on o.location_id = e.location_id
        and o.order_month = e.expense_month

)

select * from final
