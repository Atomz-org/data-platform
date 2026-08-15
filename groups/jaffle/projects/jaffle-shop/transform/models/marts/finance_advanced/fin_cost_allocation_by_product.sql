with

product_revenue as (
    select
        product_id,
        sum(daily_revenue) as product_revenue
    from {{ ref('fct_product_sales') }}
    group by 1
),

total_revenue as (
    select sum(product_revenue) as grand_total_revenue from product_revenue
),

total_expenses as (
    select sum(expense_amount) as grand_total_expense from {{ ref('fct_expenses') }}
),

allocated as (
    select
        pr.product_id,
        pr.product_revenue,
        tr.grand_total_revenue,
        te.grand_total_expense,
        case
            when tr.grand_total_revenue > 0
            then pr.product_revenue / tr.grand_total_revenue
            else 0
        end as revenue_share,
        case
            when tr.grand_total_revenue > 0
            then te.grand_total_expense * (pr.product_revenue / tr.grand_total_revenue)
            else 0
        end as allocated_overhead
    from product_revenue as pr
    cross join total_revenue as tr
    cross join total_expenses as te
),

final as (
    select
        product_id,
        product_revenue,
        revenue_share,
        allocated_overhead,
        product_revenue - allocated_overhead as product_contribution,
        case
            when product_revenue > 0
            then (product_revenue - allocated_overhead) / product_revenue * 100
            else 0
        end as contribution_margin_pct
    from allocated
)

select * from final
