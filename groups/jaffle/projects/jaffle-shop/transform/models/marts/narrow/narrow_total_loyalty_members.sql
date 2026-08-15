select count(*) as member_count from {{ ref('dim_loyalty_members') }}
