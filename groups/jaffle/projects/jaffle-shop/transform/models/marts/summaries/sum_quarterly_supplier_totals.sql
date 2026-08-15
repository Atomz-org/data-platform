with monthly as (
    select order_month, supplier_id, total_spend, count_purchase_orders
    from {{ ref('int_supplier_spend_monthly') }}
),
final as (
    select
        {{ sf_date_trunc('quarter', "order_month") }} as order_quarter,
        supplier_id,
        sum(total_spend) as quarterly_spend,
        sum(count_purchase_orders) as quarterly_pos,
        round(sum(total_spend) * 1.0 / nullif(sum(count_purchase_orders), 0), 2) as avg_po_value
    from monthly
    group by 1, 2
)
select * from final
