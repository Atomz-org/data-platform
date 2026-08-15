with

daily_pos as (
    select
        ordered_at,
        count(*) as po_count,
        sum(total_amount) as po_total_value
    from {{ ref('fct_purchase_orders') }}
    group by 1
),

trended as (
    select
        ordered_at,
        po_count,
        po_total_value,
        avg(po_count) over (order by ordered_at rows between 6 preceding and current row) as po_count_7d_ma,
        avg(po_total_value) over (order by ordered_at rows between 6 preceding and current row) as po_value_7d_ma,
        avg(po_count) over (order by ordered_at rows between 27 preceding and current row) as po_count_28d_ma,
        sum(po_total_value) over (order by ordered_at rows between 27 preceding and current row) as po_value_28d_total,
        lag(po_count, 7) over (order by ordered_at) as po_count_last_week
    from daily_pos
)

select * from trended
