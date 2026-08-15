with

daily_revenue as (

    select
        revenue_date,
        location_id,
        total_revenue
    from {{ ref('int_daily_revenue') }}

),

expenses as (

    select
        location_id,
        incurred_date,
        sum(expense_amount) as daily_expenses
    from {{ ref('stg_expenses') }}
    group by 1, 2

),

final as (

    select
        dr.revenue_date as profit_date,
        dr.location_id,
        dr.total_revenue,
        coalesce(e.daily_expenses, 0) as daily_expenses,
        dr.total_revenue - coalesce(e.daily_expenses, 0) as daily_profit,
        case
            when dr.total_revenue > 0
                then round(cast(
                    (dr.total_revenue - coalesce(e.daily_expenses, 0)) / dr.total_revenue * 100
                as {{ dbt.type_float() }}), 2)
            else null
        end as profit_margin_pct
    from daily_revenue as dr
    left join expenses as e
        on dr.location_id = e.location_id
        and dr.revenue_date = e.incurred_date

)

select * from final
