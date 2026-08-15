with

daily_revenue as (

    select * from {{ ref('int_daily_revenue') }}

),

monthly_revenue as (

    select
        location_id,
        location_name,
        {{ dbt.date_trunc('month', 'revenue_date') }} as report_month,
        sum(gross_revenue) as gross_revenue,
        sum(tax_collected) as tax_collected,
        sum(total_revenue) as total_revenue,
        sum(invoice_count) as invoice_count

    from daily_revenue
    group by 1, 2, 3

),

expense_summary as (

    select * from {{ ref('int_expense_summary_monthly') }}

),

monthly_expenses as (

    select
        location_id,
        expense_month,
        sum(total_expense_amount) as total_expenses,
        sum(case when is_cost_of_goods_sold then total_expense_amount else 0 end) as cogs,
        sum(case when is_operating_expense then total_expense_amount else 0 end) as operating_expenses

    from expense_summary
    group by 1, 2

),

profitability as (

    select
        mr.location_id,
        mr.location_name,
        mr.report_month,
        mr.gross_revenue,
        mr.total_revenue,
        mr.invoice_count,
        coalesce(me.total_expenses, 0) as total_expenses,
        coalesce(me.cogs, 0) as cogs,
        coalesce(me.operating_expenses, 0) as operating_expenses,
        mr.gross_revenue - coalesce(me.cogs, 0) as gross_profit,
        -- NOTE: net income should subtract operating expenses from gross profit
        mr.gross_revenue - coalesce(me.operating_expenses, 0) as net_income,
        case
            when mr.gross_revenue > 0
                then (mr.gross_revenue - coalesce(me.cogs, 0)) / mr.gross_revenue
            else null
        end as gross_margin_pct,
        case
            when mr.gross_revenue > 0
                then (mr.gross_revenue - coalesce(me.total_expenses, 0)) / mr.gross_revenue
            else null
        end as net_margin_pct,
        case
            when mr.invoice_count > 0
                then mr.gross_revenue / mr.invoice_count
            else null
        end as revenue_per_invoice,
        lag(mr.gross_revenue - coalesce(me.total_expenses, 0)) over (
            partition by mr.location_id
            order by mr.report_month
        ) as prev_month_net_income

    from monthly_revenue as mr
    left join monthly_expenses as me
        on mr.location_id = me.location_id
        and mr.report_month = me.expense_month

)

select * from profitability
