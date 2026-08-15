with

daily_gc as (
    select
        issued_date as activation_date,
        count(*) as cards_activated,
        sum(initial_balance) as total_loaded
    from {{ ref('dim_gift_cards') }}
    group by 1
),

trended as (
    select
        activation_date,
        cards_activated,
        total_loaded,
        avg(cards_activated) over (order by activation_date rows between 6 preceding and current row) as cards_7d_ma,
        avg(total_loaded) over (order by activation_date rows between 6 preceding and current row) as loaded_7d_ma,
        sum(cards_activated) over (order by activation_date rows between 27 preceding and current row) as cards_28d_total,
        sum(total_loaded) over (order by activation_date rows between 27 preceding and current row) as loaded_28d_total,
        lag(cards_activated, 7) over (order by activation_date) as cards_same_day_last_week
    from daily_gc
)

select * from trended
