with

purchase_orders as (
    select * from {{ ref('stg_purchase_orders') }}
),

po_receipts as (
    select * from {{ ref('stg_po_receipts') }}
),

first_receipt_per_po as (
    select
        purchase_order_id,
        min(received_at) as first_received_at
    from po_receipts
    group by purchase_order_id
),

lead_times as (
    select
        po.supplier_id,
        po.purchase_order_id,
        po.ordered_at,
        fr.first_received_at,
        {{ dbt.datediff('po.ordered_at', 'fr.first_received_at', 'day') }} as actual_lead_time_days
    from purchase_orders as po
    inner join first_receipt_per_po as fr
        on po.purchase_order_id = fr.purchase_order_id
),

monthly as (
    select
        supplier_id,
        {{ dbt.date_trunc('month', 'first_received_at') }} as month_start,
        avg(actual_lead_time_days) as avg_lead_time_days,
        stddev(actual_lead_time_days) as lead_time_std_dev
    from lead_times
    group by supplier_id, {{ dbt.date_trunc('month', 'first_received_at') }}
),

supplier_names as (
    select supplier_id, supplier_name
    from {{ ref('dim_suppliers') }}
),

with_trend as (
    select
        lt.supplier_id,
        sn.supplier_name,
        lt.month_start,
        lt.avg_lead_time_days,
        lt.lead_time_std_dev,
        lag(lt.avg_lead_time_days) over (
            partition by lt.supplier_id order by lt.month_start
        ) as prev_month_lead_time,
        avg(lt.avg_lead_time_days) over (
            partition by lt.supplier_id order by lt.month_start
            rows between 2 preceding and current row
        ) as lead_time_3m_avg
    from monthly as lt
    inner join supplier_names as sn on lt.supplier_id = sn.supplier_id
),

final as (
    select
        supplier_id,
        supplier_name,
        month_start,
        avg_lead_time_days,
        lead_time_std_dev,
        prev_month_lead_time,
        lead_time_3m_avg,
        avg_lead_time_days - coalesce(prev_month_lead_time, avg_lead_time_days) as lead_time_change,
        case
            when avg_lead_time_days > lead_time_3m_avg * 1.2 then 'deteriorating'
            when avg_lead_time_days < lead_time_3m_avg * 0.8 then 'improving'
            else 'stable'
        end as trend_direction
    from with_trend
)

select * from final
