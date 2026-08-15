with

revenue_date as (

    select
        revenue_date,
        sum(total_revenue) as total_daily_revenue

    from {{ ref('int_daily_revenue') }}
    group by revenue_date

),

daily_expenses as (

    select
        incurred_date,
        sum(expense_amount) as total_daily_expenses

    from {{ ref('fct_expenses') }}
    group by incurred_date

),

daily_cash as (

    select
        coalesce(r.revenue_date, e.incurred_date) as cash_date,
        coalesce(r.total_daily_revenue, 0) as daily_inflow,
        coalesce(e.total_daily_expenses, 0) as daily_outflow,
        coalesce(r.total_daily_revenue, 0) - coalesce(e.total_daily_expenses, 0) as net_daily_cash_flow

    from revenue_date r
    full outer join daily_expenses e on r.revenue_date = e.incurred_date

)

select
    cash_date,
    daily_inflow,
    daily_outflow,
    net_daily_cash_flow,
    sum(net_daily_cash_flow) over (order by cash_date) as cumulative_cash_position

from daily_cash
order by cash_date
