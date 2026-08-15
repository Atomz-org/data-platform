with

purchase_orders as (

    select
        purchase_order_id,
        supplier_id,
        ordered_at,
        expected_delivery_at,
        po_status,
        total_amount,
        {{ dbt.datediff('ordered_at', 'expected_delivery_at', 'day') }} as payment_term_days
    from {{ ref('fct_purchase_orders') }}

),

supplier_names as (

    select supplier_id, supplier_name
    from {{ ref('dim_suppliers') }}

),

summary as (

    select
        po.supplier_id,
        sn.supplier_name,
        count(*) as total_pos,
        avg(po.payment_term_days) as avg_payment_term_days,
        min(po.payment_term_days) as min_payment_term_days,
        max(po.payment_term_days) as max_payment_term_days,
        sum(po.total_amount) as total_spend,
        sum(case when po.po_status = 'completed' then 1 else 0 end) as completed_pos,
        case
            when avg(po.payment_term_days) <= 15 then 'net_15'
            when avg(po.payment_term_days) <= 30 then 'net_30'
            when avg(po.payment_term_days) <= 45 then 'net_45'
            else 'net_60_plus'
        end as implied_payment_terms
    from purchase_orders as po
    inner join supplier_names as sn on po.supplier_id = sn.supplier_id
    group by 1, 2

)

select * from summary
