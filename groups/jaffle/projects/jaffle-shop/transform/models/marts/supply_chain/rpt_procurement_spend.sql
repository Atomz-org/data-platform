with

supplier_spend_monthly as (

    select * from {{ ref('int_supplier_spend_monthly') }}

),

monthly_totals as (

    select
        order_month,
        sum(total_spend) as total_monthly_spend,
        sum(count_purchase_orders) as total_purchase_orders,
        sum(total_quantity_ordered) as total_quantity_ordered,
        count(distinct supplier_id) as active_supplier_count

    from supplier_spend_monthly

    group by order_month

),

supplier_detail as (

    select
        supplier_spend_monthly.supplier_id,
        supplier_spend_monthly.supplier_name,
        supplier_spend_monthly.order_month,
        supplier_spend_monthly.total_spend,
        supplier_spend_monthly.count_purchase_orders,
        supplier_spend_monthly.total_quantity_ordered,
        supplier_spend_monthly.avg_unit_cost,
        monthly_totals.total_monthly_spend,
        case
            when monthly_totals.total_monthly_spend > 0
                then supplier_spend_monthly.total_spend
                    / monthly_totals.total_monthly_spend
            else 0
        end as spend_share_of_month

    from supplier_spend_monthly

    inner join monthly_totals
        on supplier_spend_monthly.order_month = monthly_totals.order_month

)

select * from supplier_detail
