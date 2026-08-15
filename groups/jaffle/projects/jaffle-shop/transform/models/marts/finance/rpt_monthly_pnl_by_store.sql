with

monthly_revenue as (

    select
        location_id,
        location_name,
        {{ dbt.date_trunc('month', 'revenue_date') }} as report_month,
        sum(gross_revenue) as gross_revenue,
        sum(tax_collected) as tax_collected,
        sum(total_revenue) as total_revenue

    from {{ ref('int_daily_revenue') }}
    group by 1, 2, 3

),

monthly_expenses as (

    select
        location_id,
        expense_month as report_month,
        sum(
            case when is_cost_of_goods_sold then total_expense_amount else 0 end
        ) as total_cogs,
        sum(
            case when is_operating_expense then total_expense_amount else 0 end
        ) as total_opex,
        sum(total_expense_amount) as total_expenses

    from {{ ref('int_expense_summary_monthly') }}
    group by 1, 2

),

pnl as (

    select
        r.location_id,
        r.location_name,
        r.report_month,
        r.gross_revenue,
        r.tax_collected,
        r.total_revenue,
        coalesce(e.total_cogs, 0) as cost_of_goods_sold,
        r.gross_revenue - coalesce(e.total_cogs, 0) as gross_profit,
        coalesce(e.total_opex, 0) as operating_expenses,
        r.gross_revenue - coalesce(e.total_cogs, 0)
            - coalesce(e.total_opex, 0) as operating_income,
        coalesce(e.total_expenses, 0) as total_expenses,
        r.gross_revenue - coalesce(e.total_expenses, 0) as net_income,
        case
            when r.gross_revenue > 0
                then (r.gross_revenue - coalesce(e.total_cogs, 0))
                    / r.gross_revenue
            else 0
        end as gross_margin_pct,
        case
            when r.gross_revenue > 0
                then (r.gross_revenue - coalesce(e.total_expenses, 0))
                    / r.gross_revenue
            else 0
        end as net_margin_pct

    from monthly_revenue as r
    left join monthly_expenses as e
        on r.location_id = e.location_id
        and r.report_month = e.report_month

)

select * from pnl
