with

monthly_revenue as (

    select
        month_start,
        sum(monthly_revenue) as total_revenue,
        sum(monthly_gross_revenue) as total_gross_revenue,
        sum(monthly_orders) as total_orders
    from {{ ref('met_monthly_revenue_by_store') }}
    group by month_start

),

monthly_expenses as (

    select
        expense_month as month_start,
        sum(total_expense_amount) as total_expenses,
        sum(case when is_cost_of_goods_sold then total_expense_amount else 0 end) as cogs,
        sum(case when is_operating_expense then total_expense_amount else 0 end) as operating_expenses,
        sum(case when not is_cost_of_goods_sold and not is_operating_expense
            then total_expense_amount else 0 end) as other_expenses

    from {{ ref('int_expense_summary_monthly') }}
    group by expense_month

),

final as (

    select
        r.month_start,
        r.total_revenue,
        r.total_gross_revenue,
        r.total_orders,
        coalesce(e.total_expenses, 0) as total_expenses,
        coalesce(e.cogs, 0) as cogs,
        r.total_revenue - coalesce(e.cogs, 0) as gross_profit,
        case
            when r.total_revenue > 0
            then (r.total_revenue - coalesce(e.cogs, 0)) * 100.0 / r.total_revenue
            else 0
        end as gross_margin_pct,
        coalesce(e.operating_expenses, 0) as operating_expenses,
        r.total_revenue - coalesce(e.cogs, 0) - coalesce(e.operating_expenses, 0) as operating_profit,
        case
            when r.total_revenue > 0
            then (r.total_revenue - coalesce(e.cogs, 0) - coalesce(e.operating_expenses, 0))
                * 100.0 / r.total_revenue
            else 0
        end as operating_margin_pct,
        coalesce(e.other_expenses, 0) as other_expenses,
        r.total_revenue - coalesce(e.total_expenses, 0) as net_profit,
        case
            when r.total_revenue > 0
            then (r.total_revenue - coalesce(e.total_expenses, 0)) * 100.0 / r.total_revenue
            else 0
        end as net_profit_margin_pct,

        -- MoM changes
        lag(r.total_revenue) over (order by r.month_start) as prev_month_revenue,
        case
            when lag(r.total_revenue) over (order by r.month_start) > 0
            then (r.total_revenue - lag(r.total_revenue) over (order by r.month_start))
                * 1.0 / lag(r.total_revenue) over (order by r.month_start)
        end as mom_revenue_change

    from monthly_revenue as r

    left join monthly_expenses as e
        on r.month_start = e.month_start

)

select * from final
