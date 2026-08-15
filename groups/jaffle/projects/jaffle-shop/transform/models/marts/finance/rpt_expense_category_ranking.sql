with

expenses as (

    select * from {{ ref('fct_expenses') }}

),

category_store_totals as (

    select
        location_id,
        location_name,
        expense_category_id,
        category_name,
        is_operating_expense,
        is_cost_of_goods_sold,
        expense_month,
        count(expense_id) as expense_count,
        sum(expense_amount) as total_spend,
        avg(expense_amount) as avg_spend

    from expenses
    group by 1, 2, 3, 4, 5, 6, 7

),

ranked as (

    select
        location_id,
        location_name,
        expense_category_id,
        category_name,
        is_operating_expense,
        is_cost_of_goods_sold,
        expense_month,
        expense_count,
        total_spend,
        avg_spend,
        sum(total_spend) over (
            partition by location_id, expense_month
        ) as store_month_total_spend,
        case
            when sum(total_spend) over (
                partition by location_id, expense_month
            ) > 0
                then total_spend / sum(total_spend) over (
                    partition by location_id, expense_month
                )
            else 0
        end as spend_share_pct,
        rank() over (
            partition by location_id, expense_month
            order by total_spend desc
        ) as category_rank

    from category_store_totals

)

select * from ranked
