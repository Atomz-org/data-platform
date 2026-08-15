with

purchase_orders as (

    select * from {{ ref('stg_purchase_orders') }}

),

suppliers as (

    select
        supplier_id,
        supplier_name
    from {{ ref('stg_suppliers') }}

),

order_stats as (

    select
        po.supplier_id,
        s.supplier_name,
        count(po.purchase_order_id) as total_orders,
        min(po.ordered_at) as first_order_date,
        max(po.ordered_at) as last_order_date,
        {{ dbt.datediff('min(po.ordered_at)', 'max(po.ordered_at)', 'day') }} as days_span,
        case
            when count(po.purchase_order_id) > 1
                then round(cast(
                    {{ dbt.datediff('min(po.ordered_at)', 'max(po.ordered_at)', 'day') }}
                    * 1.0 / (count(po.purchase_order_id) - 1)
                as {{ dbt.type_float() }}), 1)
            else null
        end as avg_days_between_orders,
        sum(po.total_amount) as total_order_value,
        avg(po.total_amount) as avg_order_value
    from purchase_orders as po
    left join suppliers as s
        on po.supplier_id = s.supplier_id
    group by 1, 2

)

select * from order_stats
