with

cards as (
    select gift_card_id, latest_balance, initial_balance
    from {{ ref('dim_gift_cards') }}
),

stats as (
    select
        count(*) as total_cards,
        round(avg(latest_balance), 2) as mean_balance,
        round(avg(initial_balance), 2) as mean_initial,
        round(percentile_cont(0.50) within group (order by latest_balance), 2) as median_balance,
        round(percentile_cont(0.75) within group (order by latest_balance), 2) as p75_balance,
        sum(latest_balance) as total_outstanding
    from cards
),

bucketed as (
    select
        case
            when latest_balance = 0 then 'fully_used'
            when latest_balance < 10 then 'low_(1-10)'
            when latest_balance < 25 then 'medium_(10-25)'
            when latest_balance < 50 then 'high_(25-50)'
            else 'very_high_(50+)'
        end as balance_bucket,
        count(*) as card_count,
        round(sum(latest_balance), 2) as bucket_total
    from cards
    group by 1
)

select b.*, s.mean_balance, s.median_balance, s.total_outstanding, s.total_cards
from bucketed as b cross join stats as s
