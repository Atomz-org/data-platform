with points_data as (
    select
        loyalty_member_id,
        current_points_balance
    from {{ ref('int_loyalty_points_balance') }}
),

buckets as (
    select
        case
            when current_points_balance < 100 then '0-99'
            when current_points_balance < 500 then '100-499'
            when current_points_balance < 1000 then '500-999'
            when current_points_balance < 5000 then '1000-4999'
            else '5000+'
        end as points_bucket,
        count(*) as member_count,
        avg(current_points_balance) as avg_balance,
        min(current_points_balance) as min_balance,
        max(current_points_balance) as max_balance
    from points_data
    group by 1
)

select * from buckets
