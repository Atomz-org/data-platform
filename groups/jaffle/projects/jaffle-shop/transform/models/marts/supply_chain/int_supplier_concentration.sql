with

monthly_spend as (

    select * from {{ ref('int_supplier_spend_monthly') }}

),

total_monthly_spend as (

    select
        order_month,
        sum(total_spend) as grand_total_spend

    from monthly_spend

    group by order_month

),

supplier_share as (

    select
        monthly_spend.supplier_id,
        monthly_spend.supplier_name,
        monthly_spend.order_month,
        monthly_spend.total_spend,
        monthly_spend.count_purchase_orders,
        total_monthly_spend.grand_total_spend,
        case
            when total_monthly_spend.grand_total_spend > 0
                then monthly_spend.total_spend * 1.0
                    / total_monthly_spend.grand_total_spend
            else 0
        end as spend_share_pct

    from monthly_spend

    inner join total_monthly_spend
        on monthly_spend.order_month = total_monthly_spend.order_month

),

supplier_concentration as (

    select
        supplier_id,
        supplier_name,
        sum(total_spend) as lifetime_spend,
        avg(spend_share_pct) as avg_spend_share_pct,
        max(spend_share_pct) as max_spend_share_pct,
        count(distinct order_month) as active_months

    from supplier_share

    group by supplier_id, supplier_name

)

select * from supplier_concentration
