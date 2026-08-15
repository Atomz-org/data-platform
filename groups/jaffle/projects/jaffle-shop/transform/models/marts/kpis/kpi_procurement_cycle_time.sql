with final as (
    select
        {{ sf_date_trunc('month', "ordered_at") }} as order_month,
        supplier_id,
        round(avg(cycle_time_days), 1) as avg_cycle_time,
        min(cycle_time_days) as min_cycle_time,
        max(cycle_time_days) as max_cycle_time,
        count(*) as po_count
    from {{ ref('int_procurement_cycle_time') }}
    group by 1, 2
)
select * from final
