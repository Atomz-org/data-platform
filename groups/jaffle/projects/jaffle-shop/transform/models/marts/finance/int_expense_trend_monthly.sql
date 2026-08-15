with

expense_summary as (

    select * from {{ ref('int_expense_summary_monthly') }}

),

location_category_monthly as (

    select
        location_id,
        expense_category_id,
        category_name,
        is_operating_expense,
        is_cost_of_goods_sold,
        expense_month,
        expense_count,
        total_expense_amount,
        avg_expense_amount,
        lag(total_expense_amount) over (
            partition by location_id, expense_category_id
            order by expense_month
        ) as prev_month_expense_amount,
        lag(expense_count) over (
            partition by location_id, expense_category_id
            order by expense_month
        ) as prev_month_expense_count

    from expense_summary

),

with_trend as (

    select
        location_id,
        expense_category_id,
        category_name,
        is_operating_expense,
        is_cost_of_goods_sold,
        expense_month,
        expense_count,
        total_expense_amount,
        avg_expense_amount,
        prev_month_expense_amount,
        total_expense_amount - coalesce(prev_month_expense_amount, 0) as mom_change_amount,
        case
            when prev_month_expense_amount > 0
                then (total_expense_amount - prev_month_expense_amount)
                     / prev_month_expense_amount
            else null
        end as mom_change_pct,
        avg(total_expense_amount) over (
            partition by location_id, expense_category_id
            order by expense_month
            rows between 2 preceding and current row
        ) as rolling_3m_avg_expense

    from location_category_monthly

)

select * from with_trend
