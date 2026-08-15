with daily as (
    select revenue_date, sum(total_revenue) as total_revenue, sum(order_count) as total_orders
    from {{ ref('met_daily_revenue_by_store') }}
    group by 1
),
final as (
    select
        revenue_date,
        total_revenue,
        total_orders,
        sum(total_revenue) over (
            partition by {{ sf_date_trunc('year', "revenue_date") }} order by revenue_date
        ) as ytd_revenue,
        sum(total_orders) over (
            partition by {{ sf_date_trunc('year', "revenue_date") }} order by revenue_date
        ) as ytd_orders,
        row_number() over (
            partition by {{ sf_date_trunc('year', "revenue_date") }} order by revenue_date
        ) as day_of_year
    from daily
)
select * from final
