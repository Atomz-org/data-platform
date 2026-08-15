with

price_changes as (
    select
        price_changed_date,
        product_id,
        old_price,
        new_price,
        new_price - old_price as price_delta,
        round(new_price - old_price * 100.0 / nullif(old_price, 0), 2) as pct_change
    from {{ ref('fct_pricing_changes') }}
),

daily_summary as (
    select
        price_changed_date,
        count(*) as changes_count,
        avg(pct_change) as avg_pct_change,
        count(case when price_delta > 0 then 1 end) as price_increases,
        count(case when price_delta < 0 then 1 end) as price_decreases
    from price_changes
    group by 1
),

trended as (
    select
        price_changed_date,
        changes_count,
        avg_pct_change,
        price_increases,
        price_decreases,
        avg(changes_count) over (order by price_changed_date rows between 27 preceding and current row) as changes_28d_ma,
        avg(avg_pct_change) over (order by price_changed_date rows between 27 preceding and current row) as pct_change_28d_ma,
        sum(changes_count) over (order by price_changed_date rows between 89 preceding and current row) as changes_90d_total
    from daily_summary
)

select * from trended
