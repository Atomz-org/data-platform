with

daily_inventory as (

    select
        product_id,
        location_id,
        last_count_date,
        counted_on_hand
    from {{ ref('int_inventory_snapshot_daily') }}

),

stockout_days as (

    select
        product_id,
        location_id,
        count(*) as total_days_tracked,
        sum(case when counted_on_hand <= 0 then 1 else 0 end) as stockout_days,
        min(case when counted_on_hand <= 0 then last_count_date else null end) as first_stockout_date,
        max(case when counted_on_hand <= 0 then last_count_date else null end) as last_stockout_date
    from daily_inventory
    group by 1, 2

),

final as (

    select
        product_id,
        location_id,
        total_days_tracked,
        stockout_days,
        total_days_tracked - stockout_days as in_stock_days,
        case
            when total_days_tracked > 0
            then cast(stockout_days as {{ dbt.type_float() }}) / total_days_tracked * 100
            else 0
        end as stockout_frequency_pct,
        first_stockout_date,
        last_stockout_date,
        case
            when stockout_days = 0 then 'never_stockout'
            when cast(stockout_days as {{ dbt.type_float() }}) / total_days_tracked > 0.10 then 'frequent_stockout'
            when cast(stockout_days as {{ dbt.type_float() }}) / total_days_tracked > 0.03 then 'occasional_stockout'
            else 'rare_stockout'
        end as stockout_severity
    from stockout_days

)

select * from final
