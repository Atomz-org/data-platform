with final as (
    select
        {{ sf_date_trunc('month', "actual_arrival_at") }} as delivery_month,
        supplier_id,
        count(*) as total_deliveries,
        count(case when is_on_time then 1 end) as on_time_count,
        round(count(case when is_on_time then 1 end) * 100.0 / nullif(count(*), 0), 2) as on_time_pct
    from {{ ref('fct_deliveries') }}
    group by 1, 2
)
select * from final
