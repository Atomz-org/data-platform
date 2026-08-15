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

aging as (

    select
        po.purchase_order_id,
        po.supplier_id,
        s.supplier_name,
        po.total_amount,
        po.po_status,
        po.ordered_at,
        {{ dbt.datediff('po.ordered_at', dbt.current_timestamp(), 'day') }} as days_since_order,
        case
            when po.po_status in ('completed', 'paid') then 'paid'
            when {{ dbt.datediff('po.ordered_at', dbt.current_timestamp(), 'day') }} <= 30 then '0_30_days'
            when {{ dbt.datediff('po.ordered_at', dbt.current_timestamp(), 'day') }} <= 60 then '31_60_days'
            when {{ dbt.datediff('po.ordered_at', dbt.current_timestamp(), 'day') }} <= 90 then '61_90_days'
            else 'over_90_days'
        end as aging_bucket
    from purchase_orders as po
    left join suppliers as s
        on po.supplier_id = s.supplier_id

),

supplier_aging_summary as (

    select
        supplier_id,
        supplier_name,
        count(purchase_order_id) as total_pos,
        sum(total_amount) as total_outstanding,
        avg(days_since_order) as avg_days_payable_outstanding,
        sum(case when aging_bucket = '0_30_days' then total_amount else 0 end) as amount_0_30,
        sum(case when aging_bucket = '31_60_days' then total_amount else 0 end) as amount_31_60,
        sum(case when aging_bucket = '61_90_days' then total_amount else 0 end) as amount_61_90,
        sum(case when aging_bucket = 'over_90_days' then total_amount else 0 end) as amount_over_90
    from aging
    where aging_bucket != 'paid'
    group by 1, 2

)

select * from supplier_aging_summary
