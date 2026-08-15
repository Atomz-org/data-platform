with

daily_revenue as (

    select
        revenue_date as cash_flow_date,
        location_id,
        location_name,
        total_revenue as daily_inflow

    from {{ ref('int_daily_revenue') }}

),

daily_refunds as (

    select
        requested_date as cash_flow_date,
        location_id,
        sum(refund_amount) as daily_refund_outflow

    from {{ ref('fct_refunds') }}
    where is_approved = true
    group by 1, 2

),

daily_expenses as (

    select
        incurred_date as cash_flow_date,
        location_id,
        sum(expense_amount) as daily_expense_outflow

    from {{ ref('fct_expenses') }}
    group by 1, 2

),

cash_flow as (

    select
        dr.cash_flow_date,
        dr.location_id,
        dr.location_name,
        dr.daily_inflow,
        coalesce(drf.daily_refund_outflow, 0) as daily_refund_outflow,
        coalesce(de.daily_expense_outflow, 0) as daily_expense_outflow,
        coalesce(drf.daily_refund_outflow, 0)
            + coalesce(de.daily_expense_outflow, 0) as total_outflow,
        dr.daily_inflow
            - coalesce(drf.daily_refund_outflow, 0)
            - coalesce(de.daily_expense_outflow, 0) as net_cash_flow,
        sum(
            dr.daily_inflow
            - coalesce(drf.daily_refund_outflow, 0)
            - coalesce(de.daily_expense_outflow, 0)
        ) over (
            partition by dr.location_id
            order by dr.cash_flow_date
            rows between unbounded preceding and current row
        ) as cumulative_net_cash_flow,
        avg(
            dr.daily_inflow
            - coalesce(drf.daily_refund_outflow, 0)
            - coalesce(de.daily_expense_outflow, 0)
        ) over (
            partition by dr.location_id
            order by dr.cash_flow_date
            rows between 6 preceding and current row
        ) as rolling_7d_avg_net_cash_flow

    from daily_revenue as dr
    left join daily_refunds as drf
        on dr.cash_flow_date = drf.cash_flow_date
        and dr.location_id = drf.location_id
    left join daily_expenses as de
        on dr.cash_flow_date = de.cash_flow_date
        and dr.location_id = de.location_id

)

select * from cash_flow
