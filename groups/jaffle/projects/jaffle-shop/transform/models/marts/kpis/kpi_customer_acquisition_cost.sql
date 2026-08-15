with mkt_spend as (
    select month_start, total_marketing_spend
    from {{ ref('met_monthly_marketing_metrics') }}
),
new_cust as (
    select month_start, new_customers
    from {{ ref('met_monthly_customer_metrics') }}
),
final as (
    select
        ms.month_start,
        ms.total_marketing_spend as marketing_spend,
        nc.new_customers,
        round(ms.total_marketing_spend * 1.0 / nullif(nc.new_customers, 0), 2) as cac
    from mkt_spend as ms
    inner join new_cust as nc on ms.month_start = nc.month_start
)
select * from final
