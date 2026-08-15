with

daily_loyalty as (
    select
        transacted_at,
        count(distinct case when transaction_type = 'earn' then loyalty_member_id end) as active_earners,
        count(distinct loyalty_member_id) as active_members
    from {{ ref('fct_loyalty_transactions') }}
    group by 1
),

trended as (
    select
        transacted_at,
        active_earners,
        active_members,
        avg(active_members) over (order by transacted_at rows between 6 preceding and current row) as members_7d_ma,
        avg(active_members) over (order by transacted_at rows between 27 preceding and current row) as members_28d_ma,
        sum(active_members) over (order by transacted_at rows between 6 preceding and current row) as members_7d_total,
        lag(active_members, 7) over (order by transacted_at) as same_day_last_week
    from daily_loyalty
)

select * from trended
