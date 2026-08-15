with

daily_expenses as (
    select
        incurred_date,
        location_id,
        sum(expense_amount) as total_expenses,
        count(*) as expense_count
    from {{ ref('fct_expenses') }}
    group by 1, 2
),

trended as (
    select
        incurred_date,
        location_id,
        total_expenses,
        expense_count,
        avg(total_expenses) over (
            partition by location_id order by incurred_date
            rows between 6 preceding and current row
        ) as expense_7d_ma,
        avg(total_expenses) over (
            partition by location_id order by incurred_date
            rows between 27 preceding and current row
        ) as expense_28d_ma,
        case
            when total_expenses > avg(total_expenses) over (
                partition by location_id order by incurred_date
                rows between 27 preceding and current row
            ) * 1.5 then 'expense_spike'
            else 'normal'
        end as expense_anomaly
    from daily_expenses
)

select * from trended
