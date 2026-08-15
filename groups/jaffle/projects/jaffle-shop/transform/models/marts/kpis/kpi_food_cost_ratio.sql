with ingredient_usage as (
    select
        {{ dbt.date_trunc('month', 'order_date') }} as usage_month,
        sum(total_quantity_used) as total_quantity_used
    from {{ ref('fct_ingredient_usage') }}
    group by 1
),
rev as (
    select month_start, sum(monthly_revenue) as monthly_revenue
    from {{ ref('met_monthly_revenue_by_store') }}
    group by 1
),
final as (
    select
        iu.usage_month,
        iu.total_quantity_used,
        r.monthly_revenue,
        round(iu.total_quantity_used * 1.0 / nullif(r.monthly_revenue, 0) * 100, 2) as food_cost_ratio
    from ingredient_usage as iu
    inner join rev as r on iu.usage_month = r.month_start
)
select * from final
