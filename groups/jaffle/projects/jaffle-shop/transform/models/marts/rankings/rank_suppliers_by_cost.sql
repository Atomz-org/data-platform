with

supplier_cost as (
    select
        supplier_id,
        sum(total_amount) as total_spend,
        count(*) as po_count,
        round(sum(total_amount) * 1.0 / nullif(count(*), 0), 2) as avg_po_value
    from {{ ref('fct_purchase_orders') }}
    group by 1
),

ranked as (
    select
        supplier_id,
        total_spend,
        po_count,
        avg_po_value,
        rank() over (order by total_spend desc) as spend_rank,
        round(total_spend * 100.0 / nullif(sum(total_spend) over (), 0), 2) as spend_share_pct
    from supplier_cost
)

select * from ranked
