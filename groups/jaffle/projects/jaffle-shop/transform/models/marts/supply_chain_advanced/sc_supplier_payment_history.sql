with

purchase_orders as (

    select
        purchase_order_id,
        supplier_id,
        ordered_at,
        expected_delivery_at,
        po_status,
        total_amount
    from {{ ref('fct_purchase_orders') }}

),

supplier_names as (

    select supplier_id, supplier_name
    from {{ ref('dim_suppliers') }}

),

payment_analysis as (

    select
        po.supplier_id,
        sn.supplier_name,
        count(*) as total_orders,
        sum(case when po.po_status = 'completed' then 1 else 0 end) as completed_orders,
        sum(case
            when po.expected_delivery_at is not null and po.expected_delivery_at <= po.expected_delivery_at
            then 1 else 0
        end) as on_time_payments,
        sum(po.total_amount) as total_spend,
        avg(
            case when po.expected_delivery_at is not null
            then {{ dbt.datediff('ordered_at', 'expected_delivery_at', 'day') }}
            else null end
        ) as avg_payment_cycle_days
    from purchase_orders as po
    inner join supplier_names as sn on po.supplier_id = sn.supplier_id
    group by 1, 2

),

final as (

    select
        supplier_id,
        supplier_name,
        total_orders,
        completed_orders,
        on_time_payments,
        case
            when completed_orders > 0
            then cast(on_time_payments as {{ dbt.type_float() }}) / completed_orders * 100
            else 0
        end as on_time_payment_rate_pct,
        total_spend,
        avg_payment_cycle_days
    from payment_analysis

)

select * from final
