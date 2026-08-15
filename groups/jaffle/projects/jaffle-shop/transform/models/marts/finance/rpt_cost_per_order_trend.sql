with

cost_per_order as (

    select * from {{ ref('int_cost_per_order_by_store') }}

),

locations as (

    select * from {{ ref('stg_locations') }}

),

with_trend as (

    select
        cpo.location_id,
        l.location_name,
        cpo.report_month,
        cpo.order_count,
        cpo.total_order_revenue,
        cpo.total_expenses,
        cpo.cogs_amount,
        cpo.opex_amount,
        cpo.total_cost_per_order,
        cpo.cogs_per_order,
        cpo.opex_per_order,
        cpo.expense_to_revenue_ratio,
        lag(cpo.total_cost_per_order) over (
            partition by cpo.location_id
            order by cpo.report_month
        ) as prev_month_cost_per_order,
        case
            when lag(cpo.total_cost_per_order) over (
                partition by cpo.location_id
                order by cpo.report_month
            ) > 0
                then (cpo.total_cost_per_order - lag(cpo.total_cost_per_order) over (
                    partition by cpo.location_id
                    order by cpo.report_month
                )) / lag(cpo.total_cost_per_order) over (
                    partition by cpo.location_id
                    order by cpo.report_month
                )
            else null
        end as cost_per_order_mom_change_pct,
        avg(cpo.total_cost_per_order) over (
            partition by cpo.location_id
            order by cpo.report_month
            rows between 2 preceding and current row
        ) as rolling_3m_avg_cost_per_order

    from cost_per_order as cpo
    left join locations as l
        on cpo.location_id = l.location_id

)

select * from with_trend
