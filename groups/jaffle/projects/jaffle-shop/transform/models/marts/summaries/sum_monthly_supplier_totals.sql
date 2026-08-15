with final as (
    select
        order_month,
        supplier_id,
        total_spend,
        count_purchase_orders,
        round(total_spend * 1.0 / nullif(count_purchase_orders, 0), 2) as avg_po_value,
        lag(total_spend) over (partition by supplier_id order by order_month) as prior_month_spend
    from {{ ref('int_supplier_spend_monthly') }}
)
select * from final
