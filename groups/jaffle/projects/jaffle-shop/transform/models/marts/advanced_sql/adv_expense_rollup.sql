-- adv_expense_rollup.sql
-- Technique: ROLLUP
-- Hierarchical expense subtotals using ROLLUP on (location, category, month).
-- ROLLUP produces subtotals at each level: location+category+month, location+category,
-- location only, and a grand total -- matching natural drill-down analysis.

with expenses as (

    select * from {{ ref('fct_expenses') }}

),

expense_rollup as (

    select
        location_id,
        location_name,
        expense_category_id,
        category_name,
        expense_month,

        sum(expense_amount) as total_expense,
        count(expense_id) as expense_count,
        avg(expense_amount) as avg_expense_amount,

        -- Identify rollup level
        grouping(location_id) as is_location_rolled,
        grouping(expense_category_id) as is_category_rolled,
        grouping(expense_month) as is_month_rolled,

        case
            when grouping(expense_month) = 0 then 'detail'
            when grouping(expense_category_id) = 0 then 'location_category_subtotal'
            when grouping(location_id) = 0 then 'location_subtotal'
            else 'grand_total'
        end as rollup_level

    from expenses

    group by rollup (
        (location_id, location_name),
        (expense_category_id, category_name),
        expense_month
    )

)

select * from expense_rollup
order by
    is_location_rolled,
    location_id nulls last,
    is_category_rolled,
    category_name nulls last,
    is_month_rolled,
    expense_month nulls last
