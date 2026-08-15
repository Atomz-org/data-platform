with

pos as (

    select
        purchase_order_id,
        supplier_id,
        ordered_at,
        {{ day_of_week_number('ordered_at') }} as day_of_week,
        extract(day from ordered_at) as day_of_month,
        {{ dbt.date_trunc('week', 'ordered_at') }} as order_week,
        total_amount
    from {{ ref('stg_purchase_orders') }}

),

daily_pattern as (

    select
        day_of_week,
        count(*) as po_count,
        sum(total_amount) as total_spend,
        avg(total_amount) as avg_po_value
    from pos
    group by 1

),

weekly_pattern as (

    select
        order_week,
        count(*) as weekly_po_count,
        sum(total_amount) as weekly_spend
    from pos
    group by 1

),

final as (

    select
        dp.day_of_week,
        dp.po_count,
        dp.total_spend,
        dp.avg_po_value,
        cast(dp.po_count as {{ dbt.type_float() }})
            / nullif(sum(dp.po_count) over (), 0) * 100 as pct_of_total_pos,
        case
            when dp.day_of_week in (0, 6) then 'weekend'
            when dp.day_of_week = 1 then 'monday'
            when dp.day_of_week = 5 then 'friday'
            else 'midweek'
        end as day_category
    from daily_pattern as dp

)

select * from final
